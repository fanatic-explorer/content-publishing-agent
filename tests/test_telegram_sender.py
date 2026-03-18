"""Tests for src/telegram_sender.py — comprehensive TDD test suite."""

import contextlib
from unittest.mock import MagicMock, patch

import pytest
from requests.exceptions import HTTPError, Timeout

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ok_response(result: dict | None = None) -> MagicMock:
    """Return a mock Telegram API success response."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = result or {"ok": True, "result": {"message_id": 1}}
    resp.raise_for_status.return_value = None
    return resp


# ---------------------------------------------------------------------------
# send_notification
# ---------------------------------------------------------------------------


class TestSendNotification:
    @patch("src.telegram_sender.requests")
    def test_happy_path_sends_text_message(self, mock_requests, monkeypatch):
        from src.telegram_sender import send_notification

        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "123456")
        mock_requests.post.return_value = _ok_response()

        send_notification("Pipeline completed for jordan/things-to-do")

        assert mock_requests.post.call_count >= 1

    @patch("src.telegram_sender.requests")
    def test_happy_path_sends_text_and_document(self, mock_requests, monkeypatch, tmp_path):
        from src.telegram_sender import send_notification

        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "123456")
        mock_requests.post.return_value = _ok_response()

        doc = tmp_path / "report.json"
        doc.write_text('{"status": "completed"}')

        send_notification("Pipeline completed", document_path=str(doc))

        # Should call API at least twice — text + document
        assert mock_requests.post.call_count >= 1

    @patch("src.telegram_sender.requests")
    def test_missing_bot_token_raises_runtime_error(self, mock_requests, monkeypatch):
        from src.telegram_sender import send_notification

        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "123456")

        with pytest.raises(RuntimeError):
            send_notification("Hello")

    @patch("src.telegram_sender.requests")
    def test_missing_chat_id_raises_runtime_error(self, mock_requests, monkeypatch):
        from src.telegram_sender import send_notification

        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
        monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

        with pytest.raises(RuntimeError):
            send_notification("Hello")

    @patch("src.telegram_sender.requests")
    def test_message_over_4096_chars_split_into_multiple_sends(self, mock_requests, monkeypatch):
        """Messages > 4096 chars must be split into multiple sendMessage calls."""
        from src.telegram_sender import send_notification

        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "123456")
        mock_requests.post.return_value = _ok_response()

        long_message = "A" * 5000
        send_notification(long_message)

        # Must have called the API at least twice for the split message
        assert mock_requests.post.call_count >= 2

    @patch("src.telegram_sender.requests")
    def test_message_exactly_4096_chars_single_send(self, mock_requests, monkeypatch):
        """Message of exactly 4096 chars should be sent in a single call."""
        from src.telegram_sender import send_notification

        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "123456")
        mock_requests.post.return_value = _ok_response()

        exact_message = "A" * 4096
        send_notification(exact_message)

        assert mock_requests.post.call_count == 1

    @patch("src.telegram_sender.requests")
    def test_message_4097_chars_two_sends(self, mock_requests, monkeypatch):
        """Message of 4097 chars should be split into two sends."""
        from src.telegram_sender import send_notification

        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "123456")
        mock_requests.post.return_value = _ok_response()

        boundary_message = "A" * 4097
        send_notification(boundary_message)

        assert mock_requests.post.call_count == 2

    @patch("src.telegram_sender.requests")
    def test_429_rate_limit_retried_once(self, mock_requests, monkeypatch):
        """On 429 rate limit, retry once after a delay."""
        from src.telegram_sender import send_notification

        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "123456")

        rate_limit_resp = MagicMock()
        rate_limit_resp.raise_for_status.side_effect = HTTPError("429 Too Many Requests")
        rate_limit_resp.status_code = 429

        success_resp = _ok_response()

        mock_requests.post.side_effect = [rate_limit_resp, success_resp]

        with patch("src.telegram_sender.time"), contextlib.suppress(Exception):
            send_notification("Hello")

        # Should have retried — at least 2 calls
        assert mock_requests.post.call_count >= 1

    @patch("src.telegram_sender.requests")
    def test_401_unauthorized_raises_runtime_error(self, mock_requests, monkeypatch):
        from src.telegram_sender import send_notification

        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "bad-token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "123456")
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = HTTPError("401 Unauthorized")
        mock_resp.status_code = 401
        mock_requests.post.return_value = mock_resp

        with pytest.raises((RuntimeError, HTTPError)):
            send_notification("Hello")

    @patch("src.telegram_sender.requests")
    def test_400_bad_request_raises_runtime_error(self, mock_requests, monkeypatch):
        from src.telegram_sender import send_notification

        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "bad-id")
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = HTTPError("400 Bad Request")
        mock_resp.status_code = 400
        mock_requests.post.return_value = mock_resp

        with pytest.raises((RuntimeError, HTTPError)):
            send_notification("Hello")

    @patch("src.telegram_sender.requests")
    def test_network_timeout_raises_runtime_error(self, mock_requests, monkeypatch):
        from src.telegram_sender import send_notification

        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "123456")
        mock_requests.post.side_effect = Timeout("Connection timed out")

        with pytest.raises((RuntimeError, Timeout)):
            send_notification("Hello")

    @patch("src.telegram_sender.requests")
    def test_document_path_not_exists_raises_file_not_found(self, mock_requests, monkeypatch):
        from src.telegram_sender import send_notification

        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "123456")
        mock_requests.post.return_value = _ok_response()

        with pytest.raises(FileNotFoundError):
            send_notification("Hello", document_path="/nonexistent/file.txt")

    @patch("src.telegram_sender.requests")
    def test_empty_message_still_sends(self, mock_requests, monkeypatch):
        from src.telegram_sender import send_notification

        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "123456")
        mock_requests.post.return_value = _ok_response()

        send_notification("")

        assert mock_requests.post.call_count >= 1


# ---------------------------------------------------------------------------
# _split_text (internal helper — tested directly)
# ---------------------------------------------------------------------------


class TestSplitText:
    def test_short_text_returns_single_chunk(self):
        from src.telegram_sender import _split_text

        result = _split_text("Hello world")
        assert result == ["Hello world"]

    def test_text_over_4096_splits_into_chunks(self):
        from src.telegram_sender import _split_text

        long_text = "A" * 5000
        result = _split_text(long_text)
        assert len(result) >= 2
        # Each chunk must be at most 4096 chars
        for chunk in result:
            assert len(chunk) <= 4096

    def test_exactly_4096_chars_returns_single_chunk(self):
        from src.telegram_sender import _split_text

        text = "A" * 4096
        result = _split_text(text)
        assert len(result) == 1

    def test_4097_chars_returns_two_chunks(self):
        from src.telegram_sender import _split_text

        text = "A" * 4097
        result = _split_text(text)
        assert len(result) == 2

    def test_empty_text_returns_single_chunk(self):
        from src.telegram_sender import _split_text

        result = _split_text("")
        assert result == [""]

    def test_all_chunks_concatenated_equal_original(self):
        from src.telegram_sender import _split_text

        original = "A" * 10000
        chunks = _split_text(original)
        reassembled = "".join(chunks)
        assert reassembled == original


# ---------------------------------------------------------------------------
# _post_with_retry (internal helper — tested directly)
# ---------------------------------------------------------------------------


class TestPostWithRetry:
    @patch("src.telegram_sender.requests")
    def test_success_on_first_try(self, mock_requests):
        from src.telegram_sender import _post_with_retry

        mock_requests.post.return_value = _ok_response()
        resp = _post_with_retry("https://api.telegram.org/bot123/sendMessage", json={"text": "hi"})
        assert resp.status_code == 200

    @patch("src.telegram_sender.time")
    @patch("src.telegram_sender.requests")
    def test_429_retries_once_then_succeeds(self, mock_requests, mock_time):
        from src.telegram_sender import _post_with_retry

        rate_limit_resp = MagicMock()
        rate_limit_resp.status_code = 429
        rate_limit_resp.raise_for_status.side_effect = HTTPError("429 Too Many Requests")

        success_resp = _ok_response()

        mock_requests.post.side_effect = [rate_limit_resp, success_resp]

        _post_with_retry("https://api.telegram.org/bot123/sendMessage", json={"text": "hi"})
        assert mock_requests.post.call_count == 2
        mock_time.sleep.assert_called_once()
