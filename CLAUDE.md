# CLAUDE.md — Content Publishing Pipeline Agent

This file tells Claude Code everything it needs to know to work effectively in this codebase.

---

## Project Overview

**Content Publishing Pipeline Agent** is a Claude Code slash command (`/publish-trip`) for the Fanatic Explorer travel blog. It takes raw trip notes from a local inbox folder and produces a ready-to-review blog post draft with SEO metadata and social media content, preserving the Fanatic Explorer voice throughout.

This is Project 3 of a broader 6-month AI implementation plan for Fanatic Explorer. The blog is at fanaticexplorer.com.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| Package Manager | `uv` |
| Orchestration | Claude Code slash command (`/publish-trip`) |
| Keyword Research | Keysearch API via `requests` |
| AI Drafting | Claude Code's built-in capabilities (WebSearch, WebFetch, direct generation) |
| Storage | SQLite (`data/pipeline.db`) via Python `sqlite3` stdlib |
| Notifications | Telegram Bot API via `requests` |
| Browser Fallback | Playwright (headless Chromium) |
| Configuration | `python-dotenv` loading from `.env` |

No web framework. No Docker. No database server.

---

## Python & Package Management

This project uses **`uv`** exclusively. Never use `pip`, `pip3`, `python -m pip`, or `python -m venv`.

### Shared Virtual Environment

The venv is **shared across all fanatic-explorer projects** and lives outside this repo:

```
~/Projects/fanatic-explorer/.venv
```

### Daily uv Commands

```bash
uv add package-name          # Add a new package
uv sync                      # Sync all dependencies after git pull
uv run python src/module.py  # Run a Python script
uv run pytest tests/ -v      # Run tests
```

**Always use `uv run` to execute Python or pytest — never call `python`, `python3`, or `pytest` directly.**

---

## Project Structure

```
content-publishing-agent/
├── src/
│   ├── inbox_scanner.py        # Scan inbox destination subfolders, read files
│   ├── database.py             # SQLite state tracking (processed posts, pipeline runs)
│   ├── keyword_researcher.py   # Keysearch API for keyword difficulty + competitors
│   ├── telegram_sender.py      # Telegram Bot API — text message + file attachment
│   ├── browser_fetcher.py      # Playwright headless Chrome for blocked sites
│   └── output_writer.py        # Output file I/O, listing drafts, saving revisions
├── prompts/
│   └── voice_document.md       # Fanatic Explorer writing voice (git-tracked)
├── tests/
│   ├── test_inbox_scanner.py
│   ├── test_database.py
│   ├── test_keyword_researcher.py
│   ├── test_telegram_sender.py
│   ├── test_browser_fetcher.py
│   └── test_output_writer.py
├── data/
│   └── pipeline.db             # SQLite database (git-ignored)
├── inbox/                      # Drop raw trip notes here, organized by destination (git-ignored)
├── output/                     # Generated drafts organized by trip (git-ignored)
├── .claude/
│   ├── commands/
│   │   ├── publish-trip.md     # Main pipeline slash command
│   │   ├── revise-draft.md    # Revise existing draft with new research
│   │   ├── fact-check.md      # Verify factual claims in a draft
│   │   └── review.md           # Code review command
│   └── rules/
│       ├── coding-standards.md
│       └── testing.md
├── pyproject.toml
├── uv.lock
├── .env                        # API keys — NEVER COMMIT
├── .gitignore
├── CLAUDE.md                   # This file
└── README.md
```

---

## Environment Variables

The `.env` file must exist at the project root. It is git-ignored and must never be committed.

```bash
# Shared across fanatic-explorer projects
ANTHROPIC_OAUTH_TOKEN=         # sk-ant-oat01-... OAuth Bearer token
TELEGRAM_BOT_TOKEN=            # From @BotFather on Telegram
TELEGRAM_CHAT_ID=              # Your personal chat ID
KEYSEARCH_API_KEY=             # From Keysearch.co Settings → API Key

# Content Publishing Pipeline specific
INBOX_DIR=inbox                # Path to trip notes inbox (default: inbox)
OUTPUT_DIR=output              # Path to output directory (default: output)
DB_PATH=data/pipeline.db       # SQLite database path
VOICE_DOC_PATH=prompts/voice_document.md  # Voice document path
```

---

## Architecture and Data Flow

```
/publish-trip (Claude Code slash command)
  └─ interactive:
       1. SELECT    → list destination folders, ask user to pick one
       2. GATHER    → inbox_scanner.py reads ALL files in destination subfolder
       3. ANALYZE   → Claude classifies content by theme + location
       4. CHECK     → database.py checks if destination+post_type already processed
       5. ENRICH    → WebSearch + WebFetch + browser_fetcher.py (Viator + hotels)
       6. DRAFT     → Claude writes blog post (voice doc + notes + enrichment + keyword)
       7. SEO       → keyword_researcher.py + Claude (keyword options + titles + meta)
       8. SOCIAL    → Claude generates promotion + ongoing content ideas
     8.5. FACT-CHECK → Claude extracts claims, verifies via WebSearch + enrichment
       9. SAVE      → output_writer.py saves all outputs
      10. RECORD    → database.py marks as processed
      11. NOTIFY    → telegram_sender.py sends summary + draft attachment
```

**Three post types:** things-to-do, travel-guide, food-guide — each with different enrichment and structure.

```
/revise-draft (Claude Code slash command)
  └─ interactive:
       1. SETUP     → read voice document + conventions
       2. SELECT    → list_drafts() shows available drafts, user picks one
       3. LOAD      → read existing draft, enrichment, pipeline_log, seo
       4. DIRECTIONS → user provides research directions
       5. RESEARCH  → WebSearch + WebFetch for new content
       6. REVISE    → Claude updates draft (voice doc + directions + research)
     6.5. FACT-CHECK → Claude verifies new/modified content claims
       7. SAVE      → save_revision() overwrites draft, appends enrichment
       8. RECORD    → database.py logs revision steps (additive)
       9. NOTIFY    → telegram_sender.py sends updated draft
```

**Three post types:** things-to-do, travel-guide, food-guide — each with different enrichment and structure.

**SQLite schema (two tables):**
- `processed_posts` — one row per (destination, post_type): status, output_dir, timestamps
- `pipeline_runs` — audit log: post_id, step_name, status, timestamps, error_message

---

## Coding Conventions

### Python Style
- Python 3.11+. Use f-strings, not `.format()` or `%`.
- Type hints on all function signatures.
- Docstrings on every public function (one-line summary + Args/Returns if non-obvious).
- Line length: 100 characters maximum.
- Imports order: stdlib → third-party → local (`src/`) — one blank line between groups.
- Use `logging` for all runtime output. Never use `print()`.
- Internal helpers prefixed with `_`.

### Module Responsibilities
Each `src/` file owns exactly one external concern. Do not mix API calls across modules.

### Error Handling
- Wrap all API calls in `try/except` with specific exception types.
- Log the exception with context before re-raising or returning a fallback.
- Never silently swallow exceptions.

### Configuration
- All tuneable values come from `.env` via `os.getenv()` with sensible defaults.
- Never hardcode API keys, site URLs, or thresholds in source files.

### Tests
- Use `pytest`. No `unittest.TestCase` classes.
- Mock all external API calls using `unittest.mock.patch` or `pytest-mock`.
- Test files mirror the module they test.
- At least one happy-path and one error-path test per public function.

---

## Key APIs

### Keysearch API (Keyword Research)
- **Endpoint**: `GET https://www.keysearch.co/api/difficulty?key=<KEY>&keyword=<keyword>`
- **Returns**: `{difficulty: int, results: [{url, da, pa}]}`
- **Rate limit**: `time.sleep(1)` between calls.
- **API key**: From `KEYSEARCH_API_KEY` env var.

### Telegram Bot API (Notifications)
- **Auth**: Bot token in `TELEGRAM_BOT_TOKEN` env var.
- **Usage**: `sendMessage` (text) + `sendDocument` (draft file attachment).
- **Base URL**: `https://api.telegram.org/bot<TOKEN>/<method>`

---

## Git Workflow

```bash
git add src/specific_file.py tests/specific_test.py pyproject.toml uv.lock
git commit -m "feat: add inbox scanner with destination folder support"
git push origin main
```

Commit message prefixes: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`

**Never use `git add .` or `git add -A`** — risks accidentally staging `.env` or credentials.

---

## What to Avoid

- **Never commit `.env`** — API keys live here.
- **Never commit `data/pipeline.db`** — contains pipeline state.
- **Never hardcode credentials** anywhere in Python files.
- **Never use `pip install`** — use `uv add`.
- **Never call `python` or `pytest` directly** — always via `uv run`.
- **Never use `print()` for runtime output** — use `logging`.
- **Never call APIs in a tight loop** — add `time.sleep(1)` between calls.

---

## Useful References

- SEO Monitoring Agent (sibling project): `/Users/snehal/Projects/seo-monitoring-agent/`
- Master plan: `/Users/snehal/Projects/seo-monitoring-agent/docs/master-plan.md`
- uv docs: https://docs.astral.sh/uv/
- Keysearch API docs: https://www.keysearch.co/api/documentation
- Telegram Bot API: https://core.telegram.org/bots/api
