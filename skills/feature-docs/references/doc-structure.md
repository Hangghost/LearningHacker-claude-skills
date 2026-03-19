# Feature Doc Structure Guide

## Naming Conventions (this project)

| Doc type | Location | Filename pattern | Example |
|---|---|---|---|
| **Technical doc** | `docs/` | `FEATURE_NAME.md` | `SCAN_DATABASE.md` |
| **Progress log** (temporary) | `docs/progress/` | `HUM-XX_progress.md` | `HUM-94_progress.md` |

Rules:
- Technical docs: NO ticket prefix in filename — use descriptive UPPER_SNAKE_CASE
- Progress logs: ticket prefix required, placed in `docs/progress/`
- Progress log files are temporary — delete when the ticket closes

---

## Technical Doc: Section Menu (完整文件 depth)

Pick sections that fit. Not every doc needs all of them.

```markdown
# <Title>: <Subtitle>

## 概述 / Overview
1-2 paragraphs. What it does, why it was built, which Jira ticket.

## 設計架構 / Architecture
System diagram (ASCII), data flow, file structure.
Use for storage systems, new modules, cross-cutting changes.

## 資料庫 Schema / DB Schema  (storage features)
ER diagram, table definitions, column descriptions, index rationale.

## API 參考 / API Reference
Public methods, parameters, return values. Code examples.
Use when other code will call this module.

## 資料流 / Data Flow
Named scenarios (情境 1, 情境 2...) showing step-by-step flow.
Use for async systems, multi-path flows, or complex integrations.

## 序列化與反序列化  (serialization-heavy features)
Write/read flows, format mapping, edge cases.

## 使用方式 / Usage
How-to for: UI user, CLI, background scripts, direct code, debug queries.
Only include entry points that exist.

## 測試 / Tests
Test file, coverage table, how to run.

## 設計決策 / Design Decisions
Comparison table (option A vs B vs chosen). Include rationale.
Use only when the decision is non-obvious.

## 未來擴展 / Future Extensions
Planned but not implemented. SQL schemas, API stubs, UI improvements.
Keep brief — this is a placeholder, not a spec.
```

**Quality checklist:**
- [ ] Developer unfamiliar with this feature can understand it from the doc
- [ ] All key files mentioned with paths
- [ ] Data flow covers the main happy path
- [ ] Design decisions explain *why*, not just *what*
- [ ] Matches depth of other docs in this project
- [ ] Code/SQL examples are syntactically correct

---

## Technical Doc: Compact Template (標準文件 depth)

For refactors, enhancements, moderate fixes, and mid-scope changes.

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

---

## Progress Log Template

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

Add new dated entries at the bottom. Do not edit past entries.

---

## CHANGELOG Entry Format (this project)

```markdown
## [Unreleased] - YYYY-MM-DD (TICKET)

### 新增 (Added)

- **Feature Name (TICKET Phase N)** - YYYY-MM-DD 完成
  - ⏰/📦/🔄/📄/🖥️ **ComponentName**：1-line description
  - 🎯 **影響範圍**：N 檔案（+X/-Y 行）
```

Categories: `新增 (Added)` / `改進 (Changed)` / `修復 (Fixed)` / `移除 (Removed)`

Emoji by component: ⏰ cron, 📦 storage, 🔄 refactor, 📄 scripts, 🖥️ UI, 🔧 tools, 📊 charts, 🐛 bugfix, 🎯 impact summary.
