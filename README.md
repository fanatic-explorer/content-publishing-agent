# Content Publishing Pipeline Agent

A Claude Code slash command (`/publish-trip`) that transforms raw trip notes into polished, SEO-optimized blog posts for the [Fanatic Explorer](https://fanaticexplorer.com) travel blog.

## What It Does

Drop your raw trip notes into `inbox/<destination>/`, run `/publish-trip`, and get:

- **Blog post draft** in your exact writing voice (markdown with SEO front matter)
- **Keyword research** with difficulty scores via Keysearch API
- **SEO metadata** — title options, meta description, focus keyword
- **Social media content** — Pinterest descriptions, Instagram story captions, reel & post ideas
- **Telegram notification** when the draft is ready for review

## Three Post Types

| Type | Focus |
|------|-------|
| **Things to Do** | Attractions, activities, hidden gems + Viator tour links |
| **Travel Guide** | Logistics, seasons, accommodation + hotel links |
| **Food Guide** | Dishes, restaurants, food culture + food tour links |

## Quick Start

```bash
# Install dependencies
uv sync

# Install Playwright browser
uv run playwright install chromium

# Copy API keys from SEO agent
cp /path/to/seo-agent/.env .env  # Edit with your keys

# Run the pipeline
# In Claude Code: /publish-trip
```

## Project Structure

```
inbox/              ← Drop raw trip notes here (organized by destination)
output/             ← Generated drafts appear here
prompts/            ← Voice document for writing style
src/                ← Python utilities (inbox scanning, DB, Telegram, etc.)
tests/              ← pytest test suite
```

## Part of Fanatic Explorer AI Plan

This is **Project 3** of a 6-month AI implementation plan:

1. Prompting Library (ongoing)
2. SEO Monitoring Agent (complete)
3. **Content Publishing Pipeline** (this project)
4. Travel Data MCP (upcoming)
5. Personal Travel Planning Agent (upcoming)
