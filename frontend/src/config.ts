const env = (import.meta as any).env;

/**
 * Render's `fromService`/`property: host` injects a bare hostname with no scheme, which would
 * make every request resolve relative to the current page. Normalise it here so a value like
 * `documind-backend.onrender.com` still produces an absolute URL.
 */
function normalizeBackendUrl(raw: string): string {
  const trimmed = raw.trim().replace(/\/+$/, '');
  if (!trimmed) return '';
  if (/^https?:\/\//i.test(trimmed)) return trimmed;
  return `https://${trimmed}`;
}

const configured = env.VITE_BACKEND_URL as string | undefined;

export const BACKEND_URL = configured
  ? normalizeBackendUrl(configured)
  : env.DEV
    ? 'http://localhost:8000'
    : 'https://agentic-rag-fullstack-1.onrender.com';

export const SUPPORTED_UPLOAD_EXTENSIONS = ['pdf', 'docx', 'txt', 'md', 'markdown'];

/** Mirrors the backend's MAX_UPLOAD_MB default so oversized files fail fast in the browser. */
export const MAX_UPLOAD_MB = 25;

/** Document id of the pre-indexed demo book that every visitor can query. */
export const DEMO_DOCUMENT_ID = 'ikigai-default-doc-id';
