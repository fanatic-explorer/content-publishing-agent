"""telegram_sender.py — Send notifications and documents to a Telegram chat.

Delivers a text message and (optionally) a file attachment via the Telegram Bot API.
Reads TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID from the environment.
"""

import logging
import os
import time

import requests
from requests.exceptions import HTTPError, Timeout

logger = logging.getLogger(__name__)

# Telegram limits each message to 4096 UTF-8 characters
MAX_MSG_LEN = 4096

BASE_URL_TEMPLATE = "https://api.telegram.org/bot{token}/"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _split_text(text: str) -> list[str]:
    """Split a string into chunks of at most MAX_MSG_LEN characters.

    Args:
        text: The full message text to split.

    Returns:
        List of string chunks, each at most MAX_MSG_LEN characters long.
        Returns a single-element list containing the empty string when input is empty.
    """
    if not text:
        return [text]
    chunks: list[str] = []
    while text:
        chunks.append(text[:MAX_MSG_LEN])
        text = text[MAX_MSG_LEN:]
    return chunks


def _post_with_retry(url: str, **kwargs) -> requests.Response:
    """Perform a POST request with a single retry on 429 Too Many Requests.

    Args:
        url: The URL to POST to.
        **kwargs: Additional keyword arguments forwarded to requests.post.

    Returns:
        The successful requests.Response object.

    Raises:
        RuntimeError: On 401, 400, or Timeout errors.
        HTTPError: On any other HTTP error after the retry is exhausted.
    """
    try:
        resp = requests.post(url, **kwargs)
        resp.raise_for_status()
        return resp
    except Timeout as exc:
        raise RuntimeError(f"Telegram API request timed out: {exc}") from exc
    except HTTPError as exc:
        status = getattr(exc.response, "status_code", None)
        # Determine status code from the response or parse from the message string
        if status is None:
            msg = str(exc)
            if "401" in msg:
                status = 401
            elif "400" in msg:
                status = 400
            elif "429" in msg:
                status = 429

        if status == 401:
            raise RuntimeError("Invalid Telegram bot token") from exc
        if status == 400:
            raise RuntimeError("Invalid Telegram chat ID or bad request") from exc
        if status == 429:
            logger.warning("Telegram rate limit (429) hit — retrying once after 5 s.")
            time.sleep(5)
            try:
                resp2 = requests.post(url, **kwargs)
                resp2.raise_for_status()
                return resp2
            except Timeout as exc2:
                raise RuntimeError(f"Telegram API request timed out on retry: {exc2}") from exc2
            except HTTPError as exc2:
                raise RuntimeError(f"Telegram rate limit persists after retry: {exc2}") from exc2
        raise


def _send_message(token: str, chat_id: str, text: str) -> None:
    """Send a text message to a Telegram chat, splitting at 4096 chars if needed.

    Args:
        token: Telegram bot token.
        chat_id: Target chat ID.
        text: Full message text (may be longer than MAX_MSG_LEN).
    """
    url = f"{BASE_URL_TEMPLATE.format(token=token)}sendMessage"
    for chunk in _split_text(text):
        _post_with_retry(url, data={"chat_id": chat_id, "text": chunk}, timeout=30)


def _send_document(token: str, chat_id: str, file_path: str) -> None:
    """Send a file as a Telegram document by reading it from disk.

    Args:
        token: Telegram bot token.
        chat_id: Target chat ID.
        file_path: Absolute or relative path to the file to send.

    Raises:
        FileNotFoundError: If file_path does not exist on disk.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Document not found: {file_path}")

    filename = os.path.basename(file_path)
    url = f"{BASE_URL_TEMPLATE.format(token=token)}sendDocument"

    with open(file_path, "rb") as fh:
        file_bytes = fh.read()

    _post_with_retry(
        url,
        data={"chat_id": chat_id},
        files={"document": (filename, file_bytes, "application/octet-stream")},
        timeout=60,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def send_notification(message: str, document_path: str | None = None) -> None:
    """Send a notification message (and optionally a document) to Telegram.

    Reads TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID from the environment.
    Sends the text message first, then sends the document if document_path is provided.

    Args:
        message: The text message to send (will be split if > 4096 chars).
        document_path: Optional path to a file to attach as a document.

    Raises:
        RuntimeError: If TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID are not set,
            or if the Telegram API returns an error.
        FileNotFoundError: If document_path is provided but does not exist on disk.
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable is not set.")
    if not chat_id:
        raise RuntimeError("TELEGRAM_CHAT_ID environment variable is not set.")

    logger.info("Sending Telegram notification.")

    _send_message(token, chat_id, message)

    if document_path is not None:
        logger.info("Sending Telegram document: %s", document_path)
        _send_document(token, chat_id, document_path)
