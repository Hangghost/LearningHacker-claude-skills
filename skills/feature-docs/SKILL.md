---
name: feature-docs
version: 1.0.0
description: "Write feature documentation when a branch is complete. Produces a one-time documentation pass covering all changes in the branch. Trigger when the user says 建立文件, 寫文件, document this, write docs, 記錄, 做文件, or similar. Also called by /feature-done as part of the completion workflow. Two doc categories: (1) technical doc — permanent record of feature/fix with auto-scaled depth, (2) progress log — temporary development diary in docs/progress/."
---

# Feature Documentation Workflow

## Context

This skill is designed to run at **branch completion** — when all development on a feature/fix branch is done and you're ready to document the full scope of changes.

**Typical invocation**:
- Directly: `/feature-docs` — user wants to document the current branch
- Via `/feature-done` — called automatically as part of the feature completion workflow

**Scope**: Analyzes ALL changes on the branch (`git diff develop..HEAD`) to produce comprehensive documentation, not just the latest commit.

## Step 1: Identify Doc Category

Determine the category from context or ask:

> "這是哪種紀錄？
> 1. **技術文件** — 功能/修復的永久紀錄（會更新 CHANGELOG）
> 2. **進度日誌** — 開發過程暫時紀錄（票號完成後刪除）"

Also confirm the **Jira ticket number** if not already known.

---

## Category 1: Technical Doc

Permanent documentation for features, fixes, refactors, or enhancements. CHANGELOG is always updated.

### 1a. Assess depth

Analyze the full branch diff (`git diff develop..HEAD`, `git log develop..HEAD --oneline`) to understand the complete scope of changes, not just the latest commit.

Determine depth automatically — **do not ask the user to choose**:

| Criteria | Depth | What to produce |
|----------|-------|-----------------|
| New module, new architecture, new storage system, cross-cutting changes spanning 5+ files | **完整文件** | Full doc with section menu (see `references/doc-structure.md`) + CHANGELOG |
| Refactor, enhancement, new detection mode, moderate changes (2-5 files) | **標準文件** | 概述 + 修改方式 + 影響範圍 + CHANGELOG |
| Simple bug fix, 1-3 line change, obvious cause | **僅 CHANGELOG** | CHANGELOG entry only — no standalone doc |

When in doubt, lean toward the lighter option. A standalone doc is justified when the change is worth explaining for future maintainers.

### 1b. Survey `docs/`

Run `ls docs/` and read the first ~20 lines of any related files.

| Situation | Action |
|-----------|--------|
| No similar doc | Create `docs/<FEATURE_NAME>.md` (NO ticket prefix) |
| 1 closely related doc | Propose adding a section — confirm with user first |
| Multiple overlapping docs | Present consolidation plan, **discuss before writing** |

### 1c. Write the doc (if depth ≥ 標準文件)

**完整文件**: Read `references/doc-structure.md` for the section menu and quality checklist. Pick sections that fit the change.

**標準文件**: Use this compact format:

```markdown
# <TICKET>: <Description>

## 概述
What was changed and why. 1-2 paragraphs.

## 修改方式
What was done. Key design choices.

## 影響範圍
Files changed. Regression risk. Migration notes if any.

## 驗證方式
How to confirm it works.
```

Quality bar: a developer unfamiliar with this change should understand the what, why, and how from the doc alone.

### 1d. Update related project docs

**Always:**
- **`CHANGELOG.md`** — New `[Unreleased]` block (or append to same ticket's block). See format in `references/doc-structure.md`.
- **`README.md`** — Only if a new command, config option, page, or architectural component was added.

**Check if relevant:**
- `docs/architecture.md` — New module, mixin, or storage system added?
- `docs/TODO.md` — Mark relevant items complete.
- `docs/configuration.md` — New config keys/sections?

Decision rule: *"Is this doc now misleading or incomplete without the change?"* Yes → update. Tangential → skip.

### 1e. Report

- Doc created (path + depth) or skipped (reason)
- CHANGELOG updated
- Other docs updated (what changed) or deliberately left untouched (why)

---

## Category 2: Progress Log (Temporary)

A development diary for an ongoing ticket. **Temporary** — to be deleted when the ticket closes.

### 2a. Create or update the progress file

File: `docs/progress/<TICKET>_progress.md`

If the file doesn't exist yet, create it with this template:

```markdown
# <TICKET> 開發進度記錄

> ⚠️ 暫時性文件，票號完成後刪除

Jira: <TICKET>
功能: <Feature name>

---

## YYYY-MM-DD

### 完成
- item

### 進行中
- item

### 待處理 / 阻塞
- item

### 下一步
- item
```

If the file already exists, append a new dated entry at the bottom.

### 2b. Do NOT update CHANGELOG or other project docs

Progress logs are internal working notes — they don't belong in permanent project docs.

### 2c. Report

- File created or updated (path)
- Reminder that this is temporary and should be deleted when `<TICKET>` closes
