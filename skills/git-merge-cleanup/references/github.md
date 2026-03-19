# GitHub Platform Details

## Prerequisites

- `gh` CLI installed and authenticated (`gh auth status`)
- Remote URL contains `github.com`

## Pre-Merge: Create and Merge PR

### Step 1: Push Branch

```bash
git push -u origin <branch>
```

### Step 2: Generate PR Content

Gather context:
```bash
git log <target>..HEAD --oneline
git diff <target>...HEAD --stat
```

From commits and diff stats, generate:

```markdown
## Summary
<1-3 bullet points summarizing the change>

## Changes
<key files/modules affected>

## Test plan
- [ ] <suggested verification steps based on changes>
```

### Step 3: Create PR

```bash
gh pr create --base <target> --title "<short title>" --body "$(cat <<'EOF'
<generated content>
EOF
)"
```

Title rules:
- Under 70 characters
- Format: `type(scope): description` matching project commit style
- Extract ticket ID from branch name if present (e.g., `fix/HUM-95_...` → `fix(HUM-95): ...`)

### Step 4: Merge (Optional)

Ask user: "PR 已建立。要我幫你合併嗎？"

If yes, ask merge strategy:
- **Merge commit** (default): `gh pr merge --merge`
- **Squash**: `gh pr merge --squash`
- **Rebase**: `gh pr merge --rebase`

```bash
gh pr merge <number> --<strategy> --delete-branch
```

`--delete-branch` auto-deletes the remote branch on GitHub.

If no → "請到 GitHub 完成合併後告訴我，我會繼續清理流程。"

## Verify Merge

```bash
gh pr view <branch> --json state --jq '.state'
# Expected: "MERGED"
```

If state is not MERGED, warn and stop.

## Cleanup Notes

After `gh pr merge --delete-branch`, remote branch is already deleted.
Check before attempting remote delete:

```bash
git ls-remote --heads origin <branch>
# Empty output = already deleted, skip remote delete
```
