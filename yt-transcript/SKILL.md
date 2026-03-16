---
name: transcript
description: >
  Download and format YouTube video transcripts into clean Markdown.
  Use when user invokes /transcript with a YouTube URL.
---

# YouTube Transcript Skill

## Usage

The user will provide a YouTube URL. Download the video's subtitles, clean them up, and save as structured Markdown.

## Steps

1. **Verify yt-dlp is available:**

   ```bash
   cd /Users/chenhunglun/Documents/Procjects/LearningHacker-claude-skills && uv run yt-dlp --version
   ```

   If this fails, run `cd /Users/chenhunglun/Documents/Procjects/LearningHacker-claude-skills && uv sync` first to install dependencies.

2. **Run the transcript script:**

   ```bash
   # Basic transcript (no translation)
   cd /Users/chenhunglun/Documents/Procjects/LearningHacker-claude-skills && uv run python yt-transcript/scripts/transcript.py "<url>"

   # With real-time English→Chinese translation (requires ANTHROPIC_API_KEY)
   cd /Users/chenhunglun/Documents/Procjects/LearningHacker-claude-skills && uv run python yt-transcript/scripts/transcript.py "<url>" --translate

   # Submit batch translation (cheaper, async)
   cd /Users/chenhunglun/Documents/Procjects/LearningHacker-claude-skills && uv run python yt-transcript/scripts/transcript.py "<url>" --translate --batch

   # Fetch batch results
   cd /Users/chenhunglun/Documents/Procjects/LearningHacker-claude-skills && uv run python yt-transcript/scripts/transcript.py --fetch <batch_id>
   ```

   Replace `<url>` with the YouTube URL the user provided.
   If the user asks for translation, add `--translate`. Use `--batch` for long videos to save cost.

3. **On success:** The script prints the saved file path. Tell the user where the transcript was saved and offer to open or read it.

4. **On failure:** Show the error message from the script. Common issues:
   - No subtitles available for the video → suggest a different video or manual transcription
   - Invalid URL → ask user to verify the URL
   - Network error → ask user to check their connection
   - Missing ANTHROPIC_API_KEY → remind user to set the env var for `--translate`
