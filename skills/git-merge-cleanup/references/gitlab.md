# GitLab Platform Details

## Prerequisites

- Remote URL contains `gitlab` (e.g., `gitlab.com` or self-hosted GitLab)
- No CLI tool required — MR operations happen in browser

## Pre-Merge: Push and Prompt User

### Step 1: Push Branch

```bash
git push -u origin <branch>
```

### Step 2: Prompt User

After push, display:

> 分支已推送到遠端。請到 GitLab 完成以下操作：
> 1. 建立 Merge Request (target: `<target>`)
> 2. Review 並合併 MR
> 3. 完成後回來告訴我「已合併」

Then **stop and wait** for user to confirm completion.

Acceptable confirmations: "done", "完成", "已合併", "merged", "ok", "好了", or similar affirmative responses.

## Verify Merge

After user confirms, verify with git:

```bash
git fetch origin
git branch -r --merged origin/<target> | grep <branch>
```

If branch appears in merged list → confirmed.

If not found, try:
```bash
# Check if remote branch was already deleted (GitLab can auto-delete)
git ls-remote --heads origin <branch>
# Empty = branch deleted on remote, likely merged

# Double-check by comparing commits
git log origin/<target> --oneline | head -20
# Look for merge commit or branch commits
```

If still uncertain → ask user: "無法確認合併狀態，MR 確實已合併了嗎？"

## Cleanup Notes

GitLab MR settings may auto-delete source branch on merge.
Check before attempting remote delete:

```bash
git ls-remote --heads origin <branch>
# Empty output = already deleted, skip remote delete
```
