---
name: feature-start
version: 1.0.0
description: "Start development on a Jira ticket. Creates a branch and updates Jira description with the discussion plan. Trigger when the user says: /feature-start HUM-xx, 開始開發, start feature, start working on, 開工, or similar."
---

# Feature Start Workflow

## Step 1: Parse Ticket Number

Extract the Jira ticket number from user message (e.g., `HUM-98`).

If not provided, ask:
> "請提供 Jira 票號（例如 HUM-98）"

## Step 2: Read Jira Issue

- Use cloudId `34c82bd4-0b39-4bfe-bcc5-182bfb9555a0`
- Call `getJiraIssue` to get issue details (title, description, issue type)
- Present summary:

```
票號: HUM-XX
標題: <title>
類型: <issue type> (Story/Bug/Task)
描述: <description summary>
```

## Step 3: Summarize Discussion & Update Jira Description

- Review the current conversation for discussion conclusions, plans, or analysis results
- Organize into a structured format (implementation plan, root cause analysis, etc.)
- Use `editJiraIssue` to **append** the plan to the Jira issue description under a `## 實作計畫` or `## 分析結論` section (do NOT overwrite existing description)
- Show the user what will be added and **confirm before updating**

## Step 4: Create Branch

Determine branch prefix based on Jira issue type:
- **Bug** → `fix/`
- **All others** (Story, Task, etc.) → `feature/`
- User can override with `--fix` or `--feature` flag

Branch naming: `<prefix>/HUM-XX_<short_description>`
- Derive description from issue title, use snake_case, keep short

```bash
git checkout develop
git pull origin develop
git checkout -b <branch-name>
```

If `develop` doesn't exist, fallback to `main`.

## Step 5: Report

- 分支已建立: `<branch-name>`
- Jira 描述已更新（附實作計畫）
- 提醒：開始開發後，使用 `/feature-update` 提交並記錄進度

## Safety Rules

- Always confirm with user before updating Jira description
- If working tree is dirty, warn and ask user to commit or stash first
- If develop branch doesn't exist, fallback to main
