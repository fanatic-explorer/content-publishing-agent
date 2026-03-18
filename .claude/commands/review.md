---
allowed-tools: Bash(git diff:*), Bash(git log:*), Bash(git show:*), Bash(uv run pytest:*), Bash(uv run ruff:*)
description: Run a code review of content-publishing-agent changes
---

## Your task

You are a code review agent for the content-publishing-agent project. This is a READ-ONLY audit — do not modify any files.

### Step 1 — Read project conventions

Read these files FIRST before doing anything else:
- `CLAUDE.md` — project conventions
- `.claude/rules/coding-standards.md` — coding standards
- `.claude/rules/testing.md` — testing conventions

Do NOT read anything else until you have read these files.

### Step 2 — Determine scope

Change context from the user: $ARGUMENTS

**If specific files or a description is provided**: Use that as the review scope.
**If no arguments provided**: Discover changes automatically:
1. Run `git diff --name-only` for uncommitted changes
2. If working tree is clean, run `git log -1 --name-only --pretty=format:""` for the last commit
3. If that's also empty, ask the user what to review

Build the list of files to review. Exclude `data/`, `inbox/`, `output/`, and `.env` from review.

### Step 3 — Review against checklist

For each changed file, read it and check every item below. Report as PASS, WARNING, or VIOLATION.

#### A. Structural Integrity

- [ ] **A1. Imports**: All at top-level? No unused? No wildcard? Correct order (stdlib → third-party → local)?
- [ ] **A2. Config flow**: All tunables from `.env` via `os.getenv()`? No hardcoded API keys, URLs, thresholds?
- [ ] **A3. Constants vs config**: Values that look tunable (thresholds, limits) are in `.env`, not hardcoded as Python defaults?
- [ ] **A4. Module boundaries**: Each module owns one external concern? No API calls leaking across module boundaries?
- [ ] **A5. Data contracts**: Cross-module data uses documented dict shapes? No ad-hoc dict keys?
- [ ] **A6. Dead code**: No unused functions, classes, imports, or commented-out code blocks?

#### B. Error Handling

- [ ] **B1. Specific exceptions**: No bare `except` or `except Exception` unless justified?
- [ ] **B2. Logging**: Errors logged with context (which API, which keyword, what parameters) using `logging`?
- [ ] **B3. No silent swallowing**: Every exception is either logged+handled or re-raised?
- [ ] **B4. Graceful degradation**: API failures for one step don't abort the entire pipeline?
- [ ] **B5. No print()**: All runtime output uses `logging`, never `print()`?

#### C. Testing

- [ ] **C1. Coverage**: Every new public function has at least one test?
- [ ] **C2. Error paths**: At least one error-path test per public function?
- [ ] **C3. No external deps**: Unit tests mock all I/O (Keysearch, Telegram, Playwright, SQLite)?
- [ ] **C4. Realistic data**: Test inputs match actual API response shapes?

#### D. Security

- [ ] **D1. No secrets in code**: Auth tokens, API keys, passwords only from `.env`? No inline credentials?
- [ ] **D2. Git safety**: No `.env`, `credentials.json`, `data/*.db` being staged?
- [ ] **D3. No dangerous defaults**: `os.getenv()` defaults don't contain real credentials or URLs?

#### E. Documentation

- [ ] **E1. Docstrings**: Module-level and public function docstrings present and accurate?
- [ ] **E2. Type hints**: All function signatures have type hints?
- [ ] **E3. CLAUDE.md**: Updated if project structure, commands, or conventions changed?

### Step 4 — Produce verdict

```
REQUEST CHANGES — if ANY VIOLATION items exist
APPROVE WITH NOTES — if only WARNING items (no violations)
APPROVE — if all items PASS
```

### Output format

```markdown
## Code Review: {change description}

### Summary
{APPROVE / APPROVE WITH NOTES / REQUEST CHANGES}
{1-2 sentence verdict}

### Checklist
{All items from sections A through E}
{Format: PASS/WARNING/VIOLATION per item with brief detail}

### Issues
{All VIOLATION and WARNING items, each with:}

#### VIOLATION: {title}
**File**: path/to/file.py line N
**Rule**: {which checklist item}
**Detail**: {what's wrong}
**Fix**: {specific fix}

#### WARNING: {title}
...

### Notes
{Architectural observations or improvement suggestions}
```
