import os
import time
import logging
import httpx
from groq import Groq, APIConnectionError, APITimeoutError, RateLimitError
from config import GROQ_API_KEY

_client = None

def get_groq_client():
    global _client

    if _client is None:
        if not GROQ_API_KEY:
            return None

        # Create a custom HTTP client tailored for corporate networks/VPNs
        custom_http_client = httpx.Client(
            verify=False,  # Bypasses corporate SSL interception (Zscaler, etc.)
            timeout=60.0   # Increases timeout to account for proxy routing
        )

        # Initialize Groq with the custom client
        _client = Groq(
            api_key=GROQ_API_KEY,
            http_client=custom_http_client
        )

    return _client


def create_chat_completion(client, *, max_retries: int = 3, backoff_factor: float = 1.0, stream: bool = False, **kwargs):
    """Call `client.chat.completions.create` with retries on connection/timeouts."""
    
    if client is None:
        raise APIConnectionError(request=None)

    # Compatibility mapping: allow callers to use `max_tokens` like OpenAI SDKs
    if "max_tokens" in kwargs and "max_completion_tokens" not in kwargs:
        kwargs["max_completion_tokens"] = kwargs.pop("max_tokens")

    attempt = 0
    while True:
        try:
            return client.chat.completions.create(stream=stream, **kwargs) if stream else client.chat.completions.create(**kwargs)
        except (APIConnectionError, APITimeoutError, RateLimitError) as e:
            attempt += 1
            if attempt >= max_retries:
                logging.exception("Groq API request failed after %s attempts", attempt)
                raise
            sleep_for = backoff_factor * (2 ** (attempt - 1))
            logging.warning("Groq API request failed (attempt %s/%s): %s — retrying in %ss", attempt, max_retries, str(e), sleep_for)
            time.sleep(sleep_for)


def stream_chat_completion(client, **kwargs):
    """Convenience helper to call the Groq streaming API and yield text chunks."""
    kwargs.setdefault("stream", True)
    
    if "max_tokens" in kwargs and "max_completion_tokens" not in kwargs:
        kwargs["max_completion_tokens"] = kwargs.pop("max_tokens")

    it = create_chat_completion(client, stream=True, **kwargs)
    for chunk in it:
        yield chunk