---
paths:
  - "tests/**"
---
# Testing Conventions

## Framework

- Use `pytest`. No `unittest.TestCase` classes.
- Run with: `uv run pytest tests/ -v`
- Never call `python` or `pytest` directly — always via `uv run`.

## File Organization

Test files mirror the module they test:

| Source Module | Test File |
|---------------|-----------|
| `src/database.py` | `tests/test_database.py` |
| `src/inbox_scanner.py` | `tests/test_inbox_scanner.py` |
| `src/keyword_researcher.py` | `tests/test_keyword_researcher.py` |
| `src/telegram_sender.py` | `tests/test_telegram_sender.py` |
| `src/browser_fetcher.py` | `tests/test_browser_fetcher.py` |
| `src/output_writer.py` | `tests/test_output_writer.py` |

## Coverage Requirements

- At least one **happy-path** test per public function (expected input → expected output).
- At least one **error-path** test per public function (API failure → graceful handling).
- Edge cases: empty input, Unicode, boundary conditions, special characters.
- Bug fixes include a test that would have caught the original bug.

## Mocking External APIs

Mock ALL external API calls. Unit tests must never hit the network.

```python
from unittest.mock import patch, MagicMock

@patch("src.keyword_researcher.requests")
def test_keysearch_happy_path(mock_requests, monkeypatch):
    monkeypatch.setenv("KEYSEARCH_API_KEY", "test-key")
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"difficulty": 42, "results": [...]}
    mock_resp.raise_for_status.return_value = None
    mock_requests.get.return_value = mock_resp
    # ... test logic
```

Use `unittest.mock.patch` or `pytest-mock` — either is fine, be consistent within a file.

## What NOT to Test Directly

- **Never make real API calls** — Keysearch, Telegram, Playwright must all be mocked.
- **Never write to the real SQLite database** — use temp files via `tmp_path` fixture.
- **Never hit the real filesystem inbox/output** — use `tmp_path` for all file operations.

## Test Data

- Use realistic but synthetic test data that matches the shapes returned by real APIs.
- Don't invent ad-hoc data structures — mirror the actual API response shapes.
- If multiple tests need the same data, use pytest fixtures or helper functions.

## Test Structure

- Group tests by function using classes: `class TestFunctionName`
- Use `@pytest.fixture` for setup (e.g., `db_path`, `db` using `tmp_path`)
- Use `monkeypatch.setenv()` for environment variables
- Use `@patch("src.module.dependency")` for mocking
- Helper functions for building mock responses (e.g., `_ok_response()`)
