---
name: web-clip
version: 0.1.0
description: >
  Clip web articles into Markdown + images for blog reference.
  Use when user invokes /clip with a URL.
---

# Web Clip Skill

## Usage

The user will provide a web article URL. Download the article content, save as structured Markdown with images, and optionally translate to Traditional Chinese.

## Steps

1. **Run the clip script:**

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
   ```

   Replace `<url>` with the article URL the user provided.
   If the user asks for translation, add `--translate`.

2. **On success:** The script prints the saved directory path. Tell the user where the clip was saved and show the output structure.

3. **On failure:** Show the error message from the script. Common issues:
   - Could not extract article content → the site may block scraping or have unusual structure
   - Network error → ask user to check their connection
   - Missing API key → remind user to set the env var for `--translate`
