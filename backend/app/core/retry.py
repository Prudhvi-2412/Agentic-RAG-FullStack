import time
import asyncio
from google.genai.errors import APIError

try:
    from google.api_core.exceptions import ResourceExhausted
except ImportError:
    # Fallback dummy exception class if google-api-core is not installed in this environment
    class ResourceExhausted(Exception):
        pass


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
            # If it's an APIError, make sure it's a 429 Resource Exhausted/Rate Limit error
            if isinstance(e, APIError):
                code = getattr(e, "code", None)
                message = str(e)
                # Fall back to checking status code or message content
                if code != 429 and "ResourceExhausted" not in message and "429" not in message:
                    raise e
            
            if attempt == max_retries:
                print(f"Max retries ({max_retries}) reached. Raising final exception: {e}")
                raise e
                
            print(f"ResourceExhausted/429 Rate Limit caught. Retrying in {delay}s (Attempt {attempt}/{max_retries})... Error: {e}")
            time.sleep(delay)
            delay *= backoff_factor
        except Exception as e:
            raise e

async def retry_with_backoff_async(func, *args, max_retries=5, initial_delay=2, backoff_factor=2, **kwargs):
    """
    Executes an asynchronous or synchronous function with exponential backoff retries.
    """
    delay = initial_delay
    for attempt in range(1, max_retries + 1):
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        except (ResourceExhausted, APIError) as e:
            if isinstance(e, APIError):
                code = getattr(e, "code", None)
                message = str(e)
                if code != 429 and "ResourceExhausted" not in message and "429" not in message:
                    raise e
            
            if attempt == max_retries:
                print(f"Max retries ({max_retries}) reached. Raising final exception: {e}")
                raise e
                
            print(f"ResourceExhausted/429 Rate Limit caught. Retrying in {delay}s (Attempt {attempt}/{max_retries})... Error: {e}")
            await asyncio.sleep(delay)
            delay *= backoff_factor
        except Exception as e:
            raise e
