---
name: git-merge-cleanup
version: 1.0.0
description: "Git branch cleanup and conflict resolution for GitHub and GitLab. Two modes: (1) Cleanup - after PR/MR is merged, switch to target branch, pull latest, delete feature branch locally and remotely; (2) Rebase - rebase feature branch onto target and resolve conflicts using AI-assisted editing. Auto-detects platform (GitHub/GitLab) from remote URL. Trigger phrases: cleanup, 清理分支, 刪除分支, rebase, 解決衝突, merge cleanup, branch cleanup, 合併後清理, PR merged, MR merged, post-merge."
---

# Git Merge Cleanup

## Phase 0: Auto-Detect

Run all detection in parallel before starting any workflow.

### Mode Detection

Infer from user message:
- Cleanup keywords (清理, cleanup, merged, 合併完了) → **Cleanup mode**
- Rebase keywords (rebase, 衝突, conflict) → **Rebase mode**
- Ambiguous → Ask: "要執行哪種模式？(1) 合併後清理 (2) Rebase 衝突解決"

### Platform Detection

```bash
# 1. Remote URL
git remote get-url origin
# Contains "github.com" → GitHub
# Contains "gitlab"     → GitLab
# Neither               → Ask user

# 2. GitHub mode requires gh CLI
which gh  # If missing, warn and offer GitLab-style fallback
```

Load the appropriate reference file:
- GitHub → Read `references/github.md`
- GitLab → Read `references/gitlab.md`

### Target Branch Detection

```bash
# Prefer develop, fallback to main
git show-ref --verify --quiet refs/heads/develop && echo "develop" || echo "main"
```

### Current State

```bash
git branch --show-current   # Current branch
git status --short          # Uncommitted changes
git log <target>..HEAD --oneline  # Commits on this branch
```

If uncommitted changes exist, warn user and stop.

---

## Cleanup Mode

**Precondition**: PR/MR has been merged on the platform.

### Flow

1. **Pre-Merge** (platform-specific — see references/)
   - Ensure branch is pushed
   - GitHub: create PR via `gh`, optionally merge
   - GitLab: prompt user to create MR in browser, wait for confirmation
2. **Verify Merge**
   - GitHub: `gh pr view <branch> --json state` → confirm `MERGED`
   - GitLab: `git fetch origin` → `git branch -r --merged <target>` → confirm branch listed
   - If not merged → warn and stop
3. **Cleanup** (shared)
   ```bash
   git checkout <target>
   git pull origin <target>
   git branch -d <branch>           # Safe delete (ask before -D)
   # Check if remote branch still exists
   git ls-remote --heads origin <branch>
   # If exists → git push origin --delete <branch> (confirm first)
   ```
4. **Report**: branch deleted, current state, remind next steps

---

## Rebase Mode

Platform-agnostic — pure git operations.

### Flow

1. **Prepare**
   ```bash
   git fetch origin
   git checkout <target> && git pull origin <target>
   git checkout <feature-branch>
   ```
2. **Rebase**
   ```bash
   git rebase <target>
   ```
3. **If no conflicts** → skip to step 5
4. **If conflicts** → resolve loop:
   - Read each conflicted file, analyze both sides
   - Use Edit tool to resolve (remove conflict markers)
   - `git add <resolved-files>`
   - `git rebase --continue`
   - Repeat until rebase completes
   - If stuck or too complex → offer `git rebase --abort` (confirm first)
5. **Push**: Ask user before executing `git push --force`

---

## Safety Rules

All destructive operations require explicit user confirmation:
- `git branch -D` (force delete)
- `git push --force`
- `git push origin --delete`
- `git rebase --abort`
- `gh pr merge`

Never run these silently. State what will happen, then ask.
