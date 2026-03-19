---
name: feature-update
version: 1.0.0
description: "Commit changes and update Jira with development progress. One commit = one Jira comment with commit SHA. Trigger when the user says: /feature-update, commit 並更新, 更新進度, update progress, 提交進度, or similar."
---

# Feature Update Workflow

## Step 1: Gather Context

Run in parallel:
- `git status` — all changes
- `git diff --staged` and `git diff` — staged and unstaged changes
- `git branch --show-current` — current branch name
- `git log --oneline -5` — recent commits for style reference

Extract Jira ticket number from branch name (e.g., `feature/HUM-98_xxx` → `HUM-98`, `fix/HUM-95_xxx` → `HUM-95`).

If branch name doesn't contain a ticket number, ask the user.

## Step 2: Stage Changes

- If there are unstaged changes, show them to the user
- Ask which files to stage, or suggest `git add` for relevant files
- Do NOT use `git add -A` or `git add .` — prefer specific files

## Step 3: Generate Commit Message

- Analyze staged changes
- Check recent git log for the project's commit message style
- Present the commit message for confirmation:

> "建議的 commit message：\n\n`<message>`\n\n確認嗎？或請提供修改建議。"

**Wait for user confirmation. Do NOT proceed without it.**

## Step 4: Commit

Execute `git commit` with the confirmed message. Use HEREDOC format:

```bash
git commit -m "$(cat <<'EOF'
<commit message>

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

## Step 5: Update Jira

Use cloudId `34c82bd4-0b39-4bfe-bcc5-182bfb9555a0`. Add a comment to the Jira issue:

```markdown
## 開發進度更新

**Commit**: `<short-sha>`
**Message**: <commit message>

### 變更摘要
- <file1>: <what changed>
- <file2>: <what changed>
```

## Step 6: Report

- Commit: `<sha>` on branch `<branch>`
- Jira: 留言已新增至 `<ticket>`
- 提醒：下次提交使用 `/feature-update`，準備合併時使用 `/feature-done`

## Safety Rules

- Never commit without user confirming the message
- Never use `git add -A` or `git add .` without explicit user approval
- If no changes to commit, inform user and skip
