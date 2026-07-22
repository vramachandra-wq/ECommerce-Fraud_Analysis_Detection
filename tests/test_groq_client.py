"""Unit tests for ai/groq_client.py (no production code changes)."""

from unittest.mock import MagicMock, patch

import pytest
from groq import APIConnectionError, APITimeoutError, RateLimitError


@pytest.fixture(autouse=True)
def _reset_groq_client_singleton():
    import ai.groq_client as groq_client

    groq_client._client = None
    yield
    groq_client._client = None


@patch("ai.groq_client.GROQ_API_KEY", "")
def test_get_groq_client_returns_none_without_api_key():
    from ai.groq_client import get_groq_client

    assert get_groq_client() is None


@patch("ai.groq_client.Groq")
@patch("ai.groq_client.httpx.Client")
@patch("ai.groq_client.GROQ_API_KEY", "test-key")
def test_get_groq_client_creates_singleton(mock_httpx_client, mock_groq):
    from ai.groq_client import get_groq_client

    mock_instance = MagicMock()
    mock_groq.return_value = mock_instance

    first = get_groq_client()
    second = get_groq_client()

    assert first is mock_instance
    assert second is mock_instance
    mock_groq.assert_called_once()
    kwargs = mock_httpx_client.call_args.kwargs
    assert kwargs["verify"] is False
    assert kwargs["timeout"] == 60.0


def test_create_chat_completion_raises_when_client_is_none():
    from ai.groq_client import create_chat_completion

    with pytest.raises(APIConnectionError):
        create_chat_completion(None, model="x", messages=[])


def test_create_chat_completion_maps_max_tokens():
    from ai.groq_client import create_chat_completion

    client = MagicMock()
    client.chat.completions.create.return_value = "ok"

    result = create_chat_completion(
        client,
        model="test-model",
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=100,
    )

    assert result == "ok"
    kwargs = client.chat.completions.create.call_args.kwargs
    assert kwargs["max_completion_tokens"] == 100
    assert "max_tokens" not in kwargs


@patch("ai.groq_client.time.sleep")
def test_create_chat_completion_retries_then_succeeds(mock_sleep):
    from ai.groq_client import create_chat_completion

    client = MagicMock()
    client.chat.completions.create.side_effect = [
        APITimeoutError(request=None),
        "ok",
    ]

    result = create_chat_completion(
        client,
        max_retries=3,
        backoff_factor=0.01,
        model="test-model",
        messages=[],
    )

    assert result == "ok"
    assert client.chat.completions.create.call_count == 2
    mock_sleep.assert_called_once()


@patch("ai.groq_client.time.sleep")
def test_create_chat_completion_raises_after_max_retries(mock_sleep):
    from ai.groq_client import create_chat_completion

    client = MagicMock()
    client.chat.completions.create.side_effect = RateLimitError(
        message="rate limited",
        response=MagicMock(status_code=429, headers={}),
        body=None,
    )

    with pytest.raises(RateLimitError):
        create_chat_completion(
            client,
            max_retries=2,
            backoff_factor=0.01,
            model="test-model",
            messages=[],
        )

    assert client.chat.completions.create.call_count == 2


def test_create_chat_completion_stream_flag():
    from ai.groq_client import create_chat_completion

    client = MagicMock()
    client.chat.completions.create.return_value = iter(["chunk"])

    result = create_chat_completion(
        client,
        stream=True,
        model="test-model",
        messages=[],
    )

    assert list(result) == ["chunk"]
    kwargs = client.chat.completions.create.call_args.kwargs
    assert kwargs["stream"] is True


def test_stream_chat_completion_current_double_stream_error():
    """Documents current production behavior: stream is passed twice."""
    from ai.groq_client import stream_chat_completion

    client = MagicMock()

    with pytest.raises(TypeError, match="multiple values for keyword argument 'stream'"):
        list(
            stream_chat_completion(
                client,
                model="test-model",
                messages=[],
                max_tokens=50,
            )
        )
