---
name: web-clip
version: 1.1.0
description: >
  Clip web articles into Markdown + images for blog reference.
  Use when user invokes /clip with a URL.
---

# Web Clip Skill

## Usage

The user will provide a web article URL. Download the article content, save as structured Markdown with images, and optionally translate to Traditional Chinese.

## Steps

1. **Ask output settings:** Use the `AskUserQuestion` tool to ask the user:
   - Question: "輸出路徑設定？"
   - Option 1: "預設路徑 (Recommended)" — description: `~/Documents/Procjects/00_work_space/brain/clips`
   - Option 2: "自訂路徑" — description: "輸入自訂的輸出資料夾路徑"

   If the user selects "自訂路徑", use their provided path as `--output-dir` argument.

2. **Run the clip script:**

   ```bash
   # Basic clip (no translation)
   cd /Users/chenhunglun/Documents/Procjects/LearningHacker-claude-skills && uv run python skills/web-clip/scripts/clip.py "<url>"

   # With English→Chinese translation (default: Anthropic claude-haiku-4-5)
   cd /Users/chenhunglun/Documents/Procjects/LearningHacker-claude-skills && uv run python skills/web-clip/scripts/clip.py "<url>" --translate

   # Use OpenAI for translation (requires OPENAI_API_KEY)
   cd /Users/chenhunglun/Documents/Procjects/LearningHacker-claude-skills && uv run python skills/web-clip/scripts/clip.py "<url>" --translate --api openai

   # Use Gemini for translation (requires GEMINI_API_KEY)
   cd /Users/chenhunglun/Documents/Procjects/LearningHacker-claude-skills && uv run python skills/web-clip/scripts/clip.py "<url>" --translate --api gemini

   # Use Grok for translation (requires XAI_API_KEY)
   cd /Users/chenhunglun/Documents/Procjects/LearningHacker-claude-skills && uv run python skills/web-clip/scripts/clip.py "<url>" --translate --api grok

   # With custom output directory
   cd /Users/chenhunglun/Documents/Procjects/LearningHacker-claude-skills && uv run python skills/web-clip/scripts/clip.py "<url>" --output-dir "/path/to/custom/dir"
   ```

   Replace `<url>` with the article URL the user provided.
   If the user asks for translation, add `--translate`.
   If the user chose a custom output path, add `--output-dir "<path>"`.

3. **On success:** The script prints the saved directory path. **Always show the full output path to the user** and show the output structure.

4. **On failure:** Show the error message from the script. Common issues:
   - Could not extract article content → the site may block scraping or have unusual structure
   - Network error → ask user to check their connection
   - Missing API key → remind user to set the env var for `--translate`
