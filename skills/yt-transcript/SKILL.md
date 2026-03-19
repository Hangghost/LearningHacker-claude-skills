---
name: transcript
version: 1.4.0
description: >
  Download and format YouTube video transcripts into clean Markdown.
  Use when user invokes /transcript with a YouTube URL.
---

# YouTube Transcript Skill

## Usage

The user will provide a YouTube URL. Download the video's subtitles, clean them up, and save as structured Markdown.

## Steps

1. **Ask output settings:** Use the `AskUserQuestion` tool to ask the user:
   - Question: "輸出路徑設定？"
   - Option 1: "預設路徑 (Recommended)" — description: `~/Documents/Procjects/00_work_space/brain/transcripts`
   - Option 2: "自訂路徑" — description: "輸入自訂的輸出資料夾路徑"

   If the user selects "自訂路徑", use their provided path as `--output-dir` argument.

2. **Verify yt-dlp is available:**

   ```bash
   cd /Users/chenhunglun/Documents/Procjects/LearningHacker-claude-skills && uv run yt-dlp --version
   ```

   If this fails, run `cd /Users/chenhunglun/Documents/Procjects/LearningHacker-claude-skills && uv sync` first to install dependencies.

3. **Run the transcript script:**

   ```bash
   # Basic transcript (no translation)
   cd /Users/chenhunglun/Documents/Procjects/LearningHacker-claude-skills && uv run python skills/yt-transcript/scripts/transcript.py "<url>"

   # With real-time English→Chinese translation (default: Anthropic claude-haiku-4-5)
   cd /Users/chenhunglun/Documents/Procjects/LearningHacker-claude-skills && uv run python skills/yt-transcript/scripts/transcript.py "<url>" --translate

   # Use OpenAI for translation (requires OPENAI_API_KEY)
   cd /Users/chenhunglun/Documents/Procjects/LearningHacker-claude-skills && uv run python skills/yt-transcript/scripts/transcript.py "<url>" --translate --api openai

   # Use Gemini for translation (requires GEMINI_API_KEY)
   cd /Users/chenhunglun/Documents/Procjects/LearningHacker-claude-skills && uv run python skills/yt-transcript/scripts/transcript.py "<url>" --translate --api gemini

   # Use Grok for translation (requires XAI_API_KEY)
   cd /Users/chenhunglun/Documents/Procjects/LearningHacker-claude-skills && uv run python skills/yt-transcript/scripts/transcript.py "<url>" --translate --api grok

   # Specify a particular model
   cd /Users/chenhunglun/Documents/Procjects/LearningHacker-claude-skills && uv run python skills/yt-transcript/scripts/transcript.py "<url>" --translate --api anthropic --model claude-sonnet-4-5-20250514

   # Submit batch translation (Anthropic only, cheaper, async)
   cd /Users/chenhunglun/Documents/Procjects/LearningHacker-claude-skills && uv run python skills/yt-transcript/scripts/transcript.py "<url>" --translate --batch

   # Fetch batch results
   cd /Users/chenhunglun/Documents/Procjects/LearningHacker-claude-skills && uv run python skills/yt-transcript/scripts/transcript.py --fetch <batch_id>

   # With custom output directory
   cd /Users/chenhunglun/Documents/Procjects/LearningHacker-claude-skills && uv run python skills/yt-transcript/scripts/transcript.py "<url>" --output-dir "/path/to/custom/dir"
   ```

   Replace `<url>` with the YouTube URL the user provided.
   If the user asks for translation, add `--translate`. Use `--batch` for long videos to save cost.
   If the user chose a custom output path, add `--output-dir "<path>"`.

4. **On success:** The script prints the saved file path. **Always show the full output path to the user** and offer to open or read it.

5. **On failure:** Show the error message from the script. Common issues:
   - No subtitles available for the video → suggest a different video or manual transcription
   - Invalid URL → ask user to verify the URL
   - Network error → ask user to check their connection
   - Missing ANTHROPIC_API_KEY → remind user to set the env var for `--translate`
