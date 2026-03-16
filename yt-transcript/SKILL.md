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
   cd /Users/chenhunglun/Documents/Procjects/LearningHacker-claude-skills/yt-transcript && uv run yt-dlp --version
   ```

   If this fails, run `cd /Users/chenhunglun/Documents/Procjects/LearningHacker-claude-skills/yt-transcript && uv sync` first to install dependencies.

2. **Run the transcript script:**

   ```bash
   cd /Users/chenhunglun/Documents/Procjects/LearningHacker-claude-skills/yt-transcript && uv run python scripts/transcript.py "<url>"
   ```

   Replace `<url>` with the YouTube URL the user provided.

3. **On success:** The script prints the saved file path. Tell the user where the transcript was saved and offer to open or read it.

4. **On failure:** Show the error message from the script. Common issues:
   - No subtitles available for the video → suggest a different video or manual transcription
   - Invalid URL → ask user to verify the URL
   - Network error → ask user to check their connection
