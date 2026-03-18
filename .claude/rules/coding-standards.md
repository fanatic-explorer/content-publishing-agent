---
paths:
  - "src/**"
---
# Coding Standards

## Single Source of Truth

| What | Where | Never In |
|------|-------|----------|
| Tunable settings (keys, URLs, thresholds) | `.env` via `os.getenv()` with defaults | Hardcoded in source files |
| Rarely-changing values (table names, date formats) | Constants at module top | Inline literals scattered across functions |
| Type contracts / data shapes | Dataclasses or typed dicts | Loose dicts with ad-hoc keys |
| SQL schema & queries | `database.py` | Other modules |

If a value could be in `.env` but is hardcoded in Python → fix it.

## Import Conventions

```python
# Standard library — top of file
import logging
import os
import time

# Third-party
from dotenv import load_dotenv

# Local (src/)
from src.database import init_db, check_processed
```

- All imports at module top level
- No unused imports
- No wildcard imports (`from x import *`)
- One blank line between stdlib, third-party, and local groups

## Module Responsibilities

Each `src/` file owns exactly one external concern:

| Module | Owns |
|--------|------|
| `inbox_scanner.py` | Filesystem scanning for inbox destination folders |
| `database.py` | SQLite read/write |
| `keyword_researcher.py` | Keysearch API |
| `telegram_sender.py` | Telegram Bot API |
| `browser_fetcher.py` | Playwright headless Chrome |
| `output_writer.py` | Output file I/O and directory structure |

Do not mix API calls across modules. Cross-module communication uses plain Python dicts or dataclasses.

## Error Handling

```python
# Correct: specific exception, logged with context, graceful degradation
try:
    data = fetch_keyword_data(keyword)
except HTTPError as e:
    logger.error(f"Keysearch API call failed for '{keyword}': {e}")
    data = {"difficulty": None, "competitors": []}
```

- Catch specific exceptions, not bare `except` or `except Exception`
- Log the exception with context before re-raising or returning a fallback
- Never silently swallow exceptions
- Use `logging` for all runtime output — never `print()`

## Docstring Convention

```python
"""Module-level docstring — what this module does and why."""

def function_name(arg: Type) -> ReturnType:
    """One-line summary.

    Args:
        arg: Description

    Returns:
        Description

    Raises:
        SpecificError: When and why
    """
```

## Python Style

- Python 3.11+. Use f-strings, not `.format()` or `%`.
- Type hints on all function signatures.
- Line length: 100 characters maximum.
- Use `logging` for all runtime output. Never use `print()`.
- Internal helper functions prefixed with `_`.
- `logger = logging.getLogger(__name__)` at module top.

## Security

- **No secrets in code**: API keys, passwords, tokens only from `.env` via `os.getenv()`.
- **Input sanitization**: Bound length and strip control characters on any user-facing or logged data.
