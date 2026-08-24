"""
Minimal Markdown-ish -> PDF renderer built on ReportLab Platypus.

Supported line markers:
    # / ## / ### / ####   headings (H1 starts a new page)
    ```lang ... ```       code block (monospace, boxed)
    ~~~ ... ~~~           ASCII diagram block (monospace, centred box)
    | a | b |             table row;  |---|  marks the header separator
    - item                bullet
    1. item               numbered item
    > text                callout / note box
    Q: text               interview question
    A: text               answer
    FU: text              follow-up question
    KEY: text             highlighted "interview key point"
    (blank)               paragraph break

Inline: **bold**, *italic*, `code`
"""

import re
from html import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    ListFlowable,
    ListItem,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

# ── Palette ───────────────────────────────────────────────────────────────────
INK = colors.HexColor("#1a2233")
ACCENT = colors.HexColor("#2563eb")
ACCENT_DARK = colors.HexColor("#1d4ed8")
MUTED = colors.HexColor("#64748b")
RULE = colors.HexColor("#cbd5e1")
CODE_BG = colors.HexColor("#f5f7fa")
CODE_BORDER = colors.HexColor("#d7dee8")
NOTE_BG = colors.HexColor("#eff6ff")
NOTE_BORDER = colors.HexColor("#bfdbfe")
KEY_BG = colors.HexColor("#fefce8")
KEY_BORDER = colors.HexColor("#fde68a")
Q_COLOR = colors.HexColor("#9333ea")
DIAG_BG = colors.HexColor("#fbfcfe")

PAGE_W, PAGE_H = A4
MARGIN = 18 * mm


def _styles():
    ss = getSampleStyleSheet()
    s = {}

    s["body"] = ParagraphStyle(
        "body", parent=ss["Normal"], fontName="Helvetica", fontSize=9.6, leading=14.2,
        textColor=INK, spaceAfter=6, alignment=TA_LEFT,
    )
    s["h1"] = ParagraphStyle(
        "h1", parent=ss["Heading1"], fontName="Helvetica-Bold", fontSize=20, leading=25,
        textColor=ACCENT_DARK, spaceBefore=0, spaceAfter=12,
    )
    s["h2"] = ParagraphStyle(
        "h2", parent=ss["Heading2"], fontName="Helvetica-Bold", fontSize=14, leading=18,
        textColor=INK, spaceBefore=14, spaceAfter=7,
        keepWithNext=1,
    )
    s["h3"] = ParagraphStyle(
        "h3", parent=ss["Heading3"], fontName="Helvetica-Bold", fontSize=11.2, leading=15,
        textColor=ACCENT_DARK, spaceBefore=11, spaceAfter=5,
        keepWithNext=1,
    )
    s["h4"] = ParagraphStyle(
        "h4", parent=ss["Heading4"], fontName="Helvetica-BoldOblique", fontSize=10, leading=13.5,
        textColor=INK, spaceBefore=9, spaceAfter=4,
        keepWithNext=1,
    )
    s["code"] = ParagraphStyle(
        "code", parent=ss["Code"], fontName="Courier", fontSize=7.6, leading=9.8,
        textColor=colors.HexColor("#0f172a"),
    )
    s["diag"] = ParagraphStyle(
        "diag", parent=ss["Code"], fontName="Courier", fontSize=7.1, leading=9.0,
        textColor=colors.HexColor("#26324a"),
    )
    s["bullet"] = ParagraphStyle(
        "bullet", parent=s["body"], spaceAfter=2.5, leading=13.6,
    )
    s["note"] = ParagraphStyle(
        "note", parent=s["body"], fontSize=9.2, leading=13.4, textColor=colors.HexColor("#1e3a8a"),
        spaceAfter=0,
    )
    s["key"] = ParagraphStyle(
        "key", parent=s["body"], fontSize=9.2, leading=13.4, textColor=colors.HexColor("#713f12"),
        spaceAfter=0,
    )
    s["q"] = ParagraphStyle(
        "q", parent=s["body"], fontName="Helvetica-Bold", fontSize=9.8, leading=13.6,
        textColor=Q_COLOR, spaceBefore=8, spaceAfter=2,
    )
    s["a"] = ParagraphStyle(
        "a", parent=s["body"], fontSize=9.5, leading=13.8, leftIndent=9, spaceAfter=3,
    )
    s["fu"] = ParagraphStyle(
        "fu", parent=s["body"], fontName="Helvetica-Oblique", fontSize=8.9, leading=12.4,
        textColor=MUTED, leftIndent=9, spaceAfter=6,
    )
    s["tcell"] = ParagraphStyle(
        "tcell", parent=s["body"], fontSize=8.4, leading=11.4, spaceAfter=0,
    )
    s["thead"] = ParagraphStyle(
        "thead", parent=s["tcell"], fontName="Helvetica-Bold", textColor=colors.white,
    )
    s["toc1"] = ParagraphStyle(
        "toc1", parent=s["body"], fontName="Helvetica-Bold", fontSize=9.8, leading=15,
        textColor=INK, spaceBefore=4,
    )
    s["toc2"] = ParagraphStyle(
        "toc2", parent=s["body"], fontSize=8.8, leading=12.4, leftIndent=13, textColor=MUTED,
    )
    s["cover_title"] = ParagraphStyle(
        "cover_title", parent=ss["Title"], fontName="Helvetica-Bold", fontSize=31, leading=37,
        textColor=ACCENT_DARK, alignment=TA_CENTER, spaceAfter=8,
    )
    s["cover_sub"] = ParagraphStyle(
        "cover_sub", parent=s["body"], fontSize=13, leading=19, alignment=TA_CENTER,
        textColor=INK, spaceAfter=5,
    )
    s["cover_small"] = ParagraphStyle(
        "cover_small", parent=s["body"], fontSize=9.5, leading=14, alignment=TA_CENTER,
        textColor=MUTED,
    )
    return s


STYLES = _styles()

_BOLD = re.compile(r"\*\*(.+?)\*\*", re.S)
_ITAL = re.compile(r"(?<![\*\w])\*(?!\s)(.+?)(?<!\s)\*(?!\*)", re.S)
_CODE = re.compile(r"`([^`]+?)`")


def inline(text: str) -> str:
    """Escape XML then apply lightweight inline markup."""
    out = escape(text, quote=False)
    out = _CODE.sub(
        lambda m: f'<font face="Courier" size="8.6" color="#b3204d">{m.group(1)}</font>', out
    )
    out = _BOLD.sub(lambda m: f"<b>{m.group(1)}</b>", out)
    out = _ITAL.sub(lambda m: f"<i>{m.group(1)}</i>", out)
    return out


def _boxed(flowables, bg, border, pad=6):
    t = Table([[flowables]], colWidths=[PAGE_W - 2 * MARGIN])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 0.6, border),
        ("LEFTPADDING", (0, 0), (-1, -1), pad + 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), pad),
        ("TOPPADDING", (0, 0), (-1, -1), pad),
        ("BOTTOMPADDING", (0, 0), (-1, -1), pad),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def _accent_bar(flowables, bg, border):
    """Callout with a coloured left bar."""
    t = Table([[flowables]], colWidths=[PAGE_W - 2 * MARGIN])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("LINEBEFORE", (0, 0), (0, -1), 2.6, border),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def _wrap_code(line: str, width: int = 108):
    """Hard-wrap over-long code lines so nothing spills off the page."""
    if len(line) <= width:
        return [line]
    parts, cur = [], line
    indent = len(cur) - len(cur.lstrip())
    pad = " " * min(indent + 4, 20)
    while len(cur) > width:
        cut = cur.rfind(" ", 0, width)
        if cut < width // 2:
            cut = width
        parts.append(cur[:cut])
        cur = pad + cur[cut:].lstrip()
    parts.append(cur)
    return parts


def _table(rows, header=True):
    if not rows:
        return Spacer(1, 1)
    ncols = max(len(r) for r in rows)
    rows = [r + [""] * (ncols - len(r)) for r in rows]

    data = []
    for i, row in enumerate(rows):
        style = STYLES["thead"] if (header and i == 0) else STYLES["tcell"]
        data.append([Paragraph(inline(c), style) for c in row])

    avail = PAGE_W - 2 * MARGIN
    # Give the first column a little more room; it is usually the label.
    if ncols == 1:
        widths = [avail]
    elif ncols == 2:
        widths = [avail * 0.34, avail * 0.66]
    else:
        first = avail * (0.26 if ncols == 3 else 0.22)
        rest = (avail - first) / (ncols - 1)
        widths = [first] + [rest] * (ncols - 1)

    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [
        ("GRID", (0, 0), (-1, -1), 0.4, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        style += [
            ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ]
    t.setStyle(TableStyle(style))
    return t


_MARKERS = ("#", "- ", "> ", "|", "```", "~~~", "Q: ", "A: ", "FU: ", "KEY: ")


def _absorb_continuations(lines, i, target):
    """
    Fold indented wrapped lines into the list item that precedes them, so a bullet written
    across three source lines renders as one bullet rather than a bullet plus two orphan
    paragraphs.
    """
    while i < len(lines):
        raw = lines[i]
        if not raw[:1].isspace():          # continuation must be indented
            break
        nxt = raw.strip()
        if not nxt or nxt.startswith(_MARKERS) or re.match(r"^\d+\.\s", nxt):
            break
        target[-1] = target[-1] + " " + nxt
        i += 1
    return i


def parse(md: str):
    """Turn the mini-markup into a list of Platypus flowables."""
    flow = []
    lines = md.split("\n")
    i = 0
    pending_bullets = []
    pending_numbers = []

    def flush_lists():
        nonlocal pending_bullets, pending_numbers
        if pending_bullets:
            flow.append(ListFlowable(
                [ListItem(Paragraph(inline(b), STYLES["bullet"]), leftIndent=13)
                 for b in pending_bullets],
                bulletType="bullet", start="•", leftIndent=13, bulletFontSize=7,
                spaceAfter=6,
            ))
            pending_bullets = []
        if pending_numbers:
            flow.append(ListFlowable(
                [ListItem(Paragraph(inline(b), STYLES["bullet"]), leftIndent=15)
                 for b in pending_numbers],
                bulletType="1", leftIndent=15, spaceAfter=6,
            ))
            pending_numbers = []

    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()
        stripped = line.strip()

        # ── fenced code ───────────────────────────────────────────────────────
        if stripped.startswith("```"):
            flush_lists()
            i += 1
            buf = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.extend(_wrap_code(lines[i].rstrip()))
                i += 1
            i += 1
            body = Preformatted("\n".join(buf) or " ", STYLES["code"])
            flow.append(_boxed(body, CODE_BG, CODE_BORDER))
            flow.append(Spacer(1, 7))
            continue

        # ── ascii diagram ─────────────────────────────────────────────────────
        if stripped.startswith("~~~"):
            flush_lists()
            i += 1
            buf = []
            while i < len(lines) and not lines[i].strip().startswith("~~~"):
                buf.extend(_wrap_code(lines[i].rstrip(), 118))
                i += 1
            i += 1
            body = Preformatted("\n".join(buf) or " ", STYLES["diag"])
            flow.append(_boxed(body, DIAG_BG, CODE_BORDER, pad=7))
            flow.append(Spacer(1, 8))
            continue

        # ── table ─────────────────────────────────────────────────────────────
        if stripped.startswith("|"):
            flush_lists()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(set(c) <= set("-: ") and c for c in cells):
                    rows.append(cells)
                i += 1
            flow.append(_table(rows))
            flow.append(Spacer(1, 8))
            continue

        # ── headings ──────────────────────────────────────────────────────────
        if stripped.startswith("#### "):
            flush_lists()
            flow.append(Paragraph(inline(stripped[5:]), STYLES["h4"]))
            i += 1
            continue
        if stripped.startswith("### "):
            flush_lists()
            flow.append(Paragraph(inline(stripped[4:]), STYLES["h3"]))
            i += 1
            continue
        if stripped.startswith("## "):
            flush_lists()
            txt = stripped[3:]
            p = Paragraph(inline(txt), STYLES["h2"])
            p._toc = (1, txt)
            flow.append(p)
            i += 1
            continue
        if stripped.startswith("# "):
            flush_lists()
            txt = stripped[2:]
            flow.append(PageBreak())
            p = Paragraph(inline(txt), STYLES["h1"])
            p._toc = (0, txt)
            flow.append(p)
            flow.append(_rule())
            i += 1
            continue

        # ── callouts / Q&A ────────────────────────────────────────────────────
        if stripped.startswith("KEY: "):
            flush_lists()
            body = Paragraph("<b>Interview key point.</b> " + inline(stripped[5:]), STYLES["key"])
            flow.append(_accent_bar(body, KEY_BG, colors.HexColor("#f59e0b")))
            flow.append(Spacer(1, 7))
            i += 1
            continue
        if stripped.startswith("> "):
            flush_lists()
            body = Paragraph(inline(stripped[2:]), STYLES["note"])
            flow.append(_accent_bar(body, NOTE_BG, ACCENT))
            flow.append(Spacer(1, 7))
            i += 1
            continue
        if stripped.startswith("Q: "):
            flush_lists()
            flow.append(Paragraph("Q. " + inline(stripped[3:]), STYLES["q"]))
            i += 1
            continue
        if stripped.startswith("A: "):
            flush_lists()
            flow.append(Paragraph(inline(stripped[3:]), STYLES["a"]))
            i += 1
            continue
        if stripped.startswith("FU: "):
            flush_lists()
            flow.append(Paragraph("Likely follow-up: " + inline(stripped[4:]), STYLES["fu"]))
            i += 1
            continue

        # ── lists ─────────────────────────────────────────────────────────────
        m = re.match(r"^(\d+)\.\s+(.*)$", stripped)
        if m:
            if pending_bullets:
                flush_lists()
            pending_numbers.append(m.group(2))
            i += 1
            i = _absorb_continuations(lines, i, pending_numbers)
            continue
        if stripped.startswith("- "):
            if pending_numbers:
                flush_lists()
            pending_bullets.append(stripped[2:])
            i += 1
            i = _absorb_continuations(lines, i, pending_bullets)
            continue

        # ── blank / paragraph ─────────────────────────────────────────────────
        if not stripped:
            flush_lists()
            i += 1
            continue

        flush_lists()
        # Join wrapped prose lines into one paragraph.
        buf = [stripped]
        i += 1
        while i < len(lines):
            nxt = lines[i].strip()
            if (not nxt or nxt.startswith(("#", "-", ">", "|", "```", "~~~"))
                    or nxt.startswith(("Q: ", "A: ", "FU: ", "KEY: "))
                    or re.match(r"^\d+\.\s", nxt)):
                break
            buf.append(nxt)
            i += 1
        flow.append(Paragraph(inline(" ".join(buf)), STYLES["body"]))

    flush_lists()
    return flow


def _rule():
    t = Table([[""]], colWidths=[PAGE_W - 2 * MARGIN], rowHeights=[2])
    t.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -1), 1.1, ACCENT),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return t


class Handbook(BaseDocTemplate):
    """Doc template with a plain cover page and numbered body pages."""

    def __init__(self, filename, title, **kw):
        super().__init__(filename, pagesize=A4,
                         leftMargin=MARGIN, rightMargin=MARGIN,
                         topMargin=MARGIN, bottomMargin=MARGIN + 4 * mm,
                         title=title, author="Project Handbook", **kw)
        frame = Frame(MARGIN, MARGIN + 4 * mm,
                      PAGE_W - 2 * MARGIN, PAGE_H - 2 * MARGIN - 4 * mm, id="body")
        self.addPageTemplates([
            PageTemplate(id="cover", frames=[frame]),
            # Decorate at page *end*: onPage fires before any content is laid out, so the
            # running header would still hold the previous chapter's title on the first
            # page of each new part.
            PageTemplate(id="body", frames=[frame], onPageEnd=self._decorate),
        ])
        self.doc_title = title
        self._chapter = ""

    def handle_documentBegin(self):
        # multiBuild runs several passes; without this the running header would start the
        # second pass still holding the last chapter title from the first.
        self._chapter = ""
        super().handle_documentBegin()

    def _decorate(self, canv, doc):
        canv.saveState()
        canv.setFont("Helvetica", 7.6)
        canv.setFillColor(MUTED)
        canv.drawString(MARGIN, PAGE_H - MARGIN + 3 * mm, self.doc_title)
        if self._chapter:
            canv.drawRightString(PAGE_W - MARGIN, PAGE_H - MARGIN + 3 * mm, self._chapter[:70])
        canv.setStrokeColor(RULE)
        canv.setLineWidth(0.4)
        canv.line(MARGIN, PAGE_H - MARGIN + 1.6 * mm, PAGE_W - MARGIN, PAGE_H - MARGIN + 1.6 * mm)
        canv.line(MARGIN, MARGIN + 2.6 * mm, PAGE_W - MARGIN, MARGIN + 2.6 * mm)
        canv.setFont("Helvetica", 8)
        canv.drawCentredString(PAGE_W / 2, MARGIN - 1.6 * mm, str(doc.page - 1))
        canv.restoreState()

    def afterFlowable(self, flowable):
        toc = getattr(flowable, "_toc", None)
        if toc is None:
            return
        level, text = toc
        if level == 0:
            self._chapter = text
        key = f"toc-{id(flowable)}"
        self.canv.bookmarkPage(key)
        self.notify("TOCEntry", (level, text, self.page - 1, key))
        self.canv.addOutlineEntry(text[:110], key, level=level, closed=(level == 0))


def build(filename: str, title: str, subtitle_lines, sections, intro_after_toc=None):
    doc = Handbook(filename, title)

    story = []

    # ── Cover ─────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 52 * mm))
    story.append(Paragraph(title, STYLES["cover_title"]))
    story.append(Spacer(1, 5 * mm))
    for line in subtitle_lines:
        story.append(Paragraph(inline(line), STYLES["cover_sub"]))
    story.append(Spacer(1, 12 * mm))
    story.append(_rule())
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(
        "Written from the actual final source code of the repository, not from the README.",
        STYLES["cover_small"]))
    story.append(NextPageTemplate("body"))
    story.append(PageBreak())

    # ── Contents ──────────────────────────────────────────────────────────────
    story.append(Paragraph("Contents", STYLES["h1"]))
    story.append(_rule())
    story.append(Spacer(1, 5))
    toc = TableOfContents()
    toc.levelStyles = [STYLES["toc1"], STYLES["toc2"]]
    toc.dotsMinLevel = 0
    story.append(toc)

    if intro_after_toc:
        story.extend(parse(intro_after_toc))

    for section in sections:
        story.extend(parse(section))

    doc.multiBuild(story)
    return filename
