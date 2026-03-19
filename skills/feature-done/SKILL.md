---
name: feature-done
version: 1.0.0
description: "Complete a feature: run quality checks, update docs, merge to develop, cleanup branch, and close Jira ticket. Trigger when the user says: /feature-done, feature 完成, 合併分支, 功能完成, merge to develop, 完成開發, or similar."
---

# Feature Done Workflow

## Step 1: Pre-flight Check

Run in parallel:
- `git branch --show-current` — must be a feature/fix branch (not main/develop)
- `git status` — working tree should be clean
- `git log develop..HEAD --oneline` — commits to be merged

Extract Jira ticket from branch name (e.g., `feature/HUM-98_xxx` → `HUM-98`).

If working tree is dirty, warn user and stop. Suggest using `/feature-update` to commit first.

Present summary:
```
分支: <branch>
票號: HUM-XX
包含 N 個 commits:
  - <commit1>
  - <commit2>
```

## Step 2: Quality Checks

Run `make git-ready` (format + lint + test).

- If checks pass → proceed
- If checks fail → show errors, attempt to fix, re-run. If unfixable, stop and inform user.

## Step 3: Update Documentation

Invoke `feature-docs` skill logic (Category 1: Technical Doc):
- Analyze all changes on this branch (`git diff develop..HEAD`)
- Auto-assess depth (完整文件 / 標準文件 / 僅 CHANGELOG)
- Update `CHANGELOG.md` with an `[Unreleased]` block for this ticket
- Create/update docs if depth warrants it
- Update `README.md` if new commands, pages, or components were added

**Important**: This is a one-time documentation pass for the entire branch, not per-commit.

## Step 4: Commit Documentation

If any docs were created or updated:
```bash
git add CHANGELOG.md docs/ README.md  # only files that actually changed
git commit -m "docs: 更新 HUM-XX 相關文件"
```

## Step 5: Merge to develop

```bash
git checkout develop
git pull origin develop
git merge --no-ff <feature-branch> -m "Merge <feature-branch> into develop (HUM-XX)"
```

If merge conflict → inform user and stop. Do NOT auto-resolve. Suggest using `git-merge-cleanup` rebase mode.

## Step 6: Push develop

```bash
git push origin develop
```

## Step 7: Delete Feature Branch

Confirm with user before deleting.

```bash
git push origin --delete <feature-branch>
git branch -d <feature-branch>
```

## Step 8: Close Jira Ticket

Use cloudId `34c82bd4-0b39-4bfe-bcc5-182bfb9555a0`.

1. Call `getTransitionsForJiraIssue` to get available transitions
2. Find the transition that moves to "Done" status
3. Execute `transitionJiraIssue` to move the ticket to Done
4. Add a closing comment:

```markdown
## 任務完成

**分支**: `<branch>` → 已合併至 `develop`
**Commits**: N 個 commits
**文件**: <doc path if created, or "僅 CHANGELOG">

任務已完成，分支已清理。可以關閉此票號。
```

## Step 9: Report

- 品質檢查: 通過
- 文件: 已更新（路徑）或僅 CHANGELOG
- 合併: `<branch>` → develop
- 分支: 已刪除（local + remote）
- Jira: HUM-XX → Done
- 下一步: 準備進版時使用 `/release`

## Safety Rules

- All destructive operations (branch delete, Jira transition) require user confirmation
- If merge conflict occurs, stop immediately — do NOT auto-resolve
- If quality checks fail, do NOT proceed with merge
- Never skip quality checks
