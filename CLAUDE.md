# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

A collection of custom Claude Code Skills. Each skill lives in its own subdirectory with a `SKILL.md` (the skill definition) and supporting code.

Skills are installed by symlinking their directory into `~/.claude/skills/`:
```bash
ln -s /path/to/claude-skills/<skill-name> ~/.claude/skills/<skill-name>
```

## Skills

### yt-transcript (`/transcript <youtube_url>`)
Downloads YouTube subtitles via yt-dlp and outputs clean Markdown to `~/transcripts/{YYYY-MM}/`.

- **Runtime:** Python ≥3.10, managed by `uv`
- **Install deps:** `cd yt-transcript && uv sync`
- **Run:** `cd yt-transcript && uv run python scripts/transcript.py "<url>"`
- **Entry point:** `yt-transcript/scripts/transcript.py` — single-file script, no package structure
- **Subtitle priority:** manual zh → en, then auto-generated en → zh
- **Phase 2 (planned):** `--translate` flag using Claude Haiku API for en→zh translation

## Conventions

- Each skill directory contains: `SKILL.md` (Claude Code reads this), `PLAN.md` (design doc), and implementation files
- Python skills use `uv` for dependency management (not pip/poetry)
- Repo language is mixed Chinese (Traditional) and English — docs/comments in Chinese, code in English
