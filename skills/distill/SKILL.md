---
name: distill
description: >
  Extract structured knowledge from interview/podcast transcripts for blog writing.
  Decomposes conversations into reusable writing materials: viewpoints with reasoning chains,
  quotable quotes, concept maps, tensions, and blog angle suggestions.
  Use when user invokes /distill with a transcript file path or wants to
  analyze an interview/podcast transcript for blog content creation.
---

# Distill — Transcript Knowledge Extraction

Transform interview/podcast transcripts into structured research notes for knowledge and tech bloggers.

## Usage

```
/distill <transcript_file>
/distill <transcript_file> --focus "<topic>"
```

- `<transcript_file>`: Path to a Markdown transcript (e.g. from `/transcript`)
- `--focus`: Optional — narrow extraction to a specific topic or question

## Workflow

1. **Read the transcript file** provided by the user.

2. **Read the extraction framework**: Load `references/extraction-framework.md` from this skill's directory for the full analysis instructions and output format.

3. **Execute the 6-step extraction** following the framework:
   - Step 1: Speaker identification & context
   - Step 2: Viewpoint extraction with reasoning chains (core output)
   - Step 3: Quotable quotes collection
   - Step 4: Terminology & concept map
   - Step 5: Tensions & controversies
   - Step 6: Blog angle suggestions

   If `--focus` is specified, prioritize viewpoints and reasoning related to that topic. Still complete all 6 steps but weight extraction toward the focus area.

4. **Save the output** to `~/distills/{YYYY-MM}/{source-title}-distill.md`, where:
   - `{YYYY-MM}` is the current year-month
   - `{source-title}` is derived from the transcript filename (strip date prefix and extension)
   - Create the directory if it does not exist

5. **Report** the saved file path to the user and offer to dive deeper into any specific viewpoint or suggest additional angles.

## Constraints

- Extract only what exists in the transcript. Never invent, speculate, or supplement with external knowledge. Mark gaps as `[原文未展開]`.
- Every extracted item must cite its source (speaker + paragraph/timestamp).
- Preserve the speaker's own terminology and definitions, not textbook definitions.
- Output language matches the transcript language.
