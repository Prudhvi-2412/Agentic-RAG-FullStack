import logging
import time

from google.genai.errors import APIError

try:
    from google.api_core.exceptions import ResourceExhausted
except ImportError:
    # Fallback dummy exception class if google-api-core is not installed in this environment
    class ResourceExhausted(Exception):
        pass

logger = logging.getLogger(__name__)


def _is_rate_limit(exc: Exception) -> bool:
    """True when the exception represents a 429/quota error worth retrying."""
    if not isinstance(exc, APIError):
        return True  # ResourceExhausted is always a quota error
    code = getattr(exc, "code", None)
    message = str(exc)
    return code == 429 or "ResourceExhausted" in message or "429" in message


def retry_with_backoff(func, *args, max_retries=5, initial_delay=2, backoff_factor=2, **kwargs):
    """
    Executes a synchronous function with exponential backoff retries when catching
    ResourceExhausted or 429 APIError exceptions.
    """
    delay = initial_delay
    for attempt in range(1, max_retries + 1):
        try:
            return func(*args, **kwargs)
        except (ResourceExhausted, APIError) as e:
            if not _is_rate_limit(e):
                raise

            if attempt == max_retries:
                logger.error("Max retries (%s) reached; raising: %s", max_retries, e)
                raise

            logger.warning(
                "Rate limited by the Gemini API. Retrying in %ss (attempt %s/%s): %s",
                delay, attempt, max_retries, e,
            )
            time.sleep(delay)
            delay *= backoff_factor
