---
name: release
description: >
  Release a skill version: bump version, update CHANGELOG, commit, and tag.
  Use when user invokes /release with a skill name.
---

# Release Skill

## Usage

```
/release <skill-name> [patch|minor|major]
```

- `skill-name`: the directory name of the skill to release (e.g. `yt-transcript`)
- Version bump type: `patch` (default), `minor`, or `major`

## Steps

1. **Determine skill and version bump:**
   - Parse the skill name and bump type from the user's input
   - If bump type is not specified, ask the user: patch (bug fix), minor (new feature), or major (breaking change)

2. **Read current version from the skill's `SKILL.md`:**
   - Look for `version:` in the YAML frontmatter of `<skill-name>/SKILL.md`
   - If no version exists, start from `0.0.0`
   - Calculate the new version by bumping the appropriate segment (reset lower segments to 0)

3. **Confirm with user:**
   - Show: skill name, current version → new version, bump type
   - List the staged/unstaged changes related to this skill (run `git diff --stat` and `git status`)
   - Ask user to confirm before proceeding

4. **Collect release notes:**
   - Ask the user to describe what changed, OR
   - Auto-generate from git log since the last tag for this skill: `git log <skill-name>/v<old>..HEAD -- <skill-name>/`
   - Format as bullet points in Traditional Chinese (matching project conventions)

5. **Update files:**
   - Update `version:` in `<skill-name>/SKILL.md` frontmatter to the new version
   - Prepend a new entry to `CHANGELOG.md` under today's date heading:
     - If today's date heading already exists, add the new skill entry under it
     - If not, create a new date heading above existing entries
     - Format: `### <skill-name> v<new-version>` followed by bullet points

6. **Commit and tag:**
   - Stage: `<skill-name>/SKILL.md`, `CHANGELOG.md`, and any other modified files belonging to this skill
   - Commit message format:
     ```
     release(<skill-name>): v<new-version>

     <bullet points of changes>
     ```
   - Create annotated git tag: `<skill-name>/v<new-version>` with the same message
   - Example: `git tag -a "yt-transcript/v1.2.0" -m "release(yt-transcript): v1.2.0"`

7. **Report result:**
   - Show the new version, tag name, and CHANGELOG entry
   - Remind user to `git push && git push --tags` if they want to publish

## Important Notes

- Do NOT push automatically — let the user decide when to push
- Always confirm with the user before committing
- If there are no changes since the last release, warn the user and ask if they still want to proceed
- The CHANGELOG.md is at the repository root: `/Users/chenhunglun/Documents/Procjects/LearningHacker-claude-skills/CHANGELOG.md`
- All skill SKILL.md files follow the pattern: `<skill-name>/SKILL.md`
