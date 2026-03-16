"""Download YouTube subtitles and format them into clean Markdown."""

import re
import sys
import tempfile
import unicodedata
import urllib.request
from pathlib import Path

import yt_dlp


# For manual subtitles: prefer Chinese, fallback to English
MANUAL_LANG_PRIORITY = ["zh-Hant", "zh-Hans", "zh", "en"]
# For auto-generated: prefer the original language (usually en for English videos)
# to avoid low-quality machine translation; Chinese only if it's the source language
AUTO_LANG_PRIORITY = ["en", "zh-Hant", "zh-Hans", "zh"]


def extract_info(url: str) -> dict:
    """Extract full video info via yt-dlp (single API call)."""
    opts = {"quiet": True, "no_warnings": True, "skip_download": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)


def get_video_info(raw_info: dict, url: str) -> dict:
    """Extract structured metadata from raw yt-dlp info."""
    return {
        "title": raw_info.get("title", "Untitled"),
        "channel": raw_info.get("channel", raw_info.get("uploader", "Unknown")),
        "upload_date": raw_info.get("upload_date", ""),
        "duration": raw_info.get("duration", 0),
        "webpage_url": raw_info.get("webpage_url", url),
    }


def _find_best_lang(available: dict, priority: list[str]) -> str | None:
    """Pick the best language from available subtitles dict."""
    for lang in priority:
        if lang in available:
            return lang
    return None


def download_subtitles(url: str, tmp_dir: str, raw_info: dict) -> Path:
    """Download subtitles using yt-dlp, trying manual then auto-generated."""
    manual_subs = raw_info.get("subtitles") or {}
    auto_subs = raw_info.get("automatic_captions") or {}
    video_lang = raw_info.get("language", "")

    # For manual subs: prefer Chinese
    chosen_lang = _find_best_lang(manual_subs, MANUAL_LANG_PRIORITY)
    use_auto = False
    if chosen_lang is None:
        # For auto subs: prefer the video's original language to avoid bad machine translation
        auto_priority = AUTO_LANG_PRIORITY
        if video_lang and video_lang.startswith("zh"):
            # Chinese source video — prefer Chinese auto-captions
            auto_priority = ["zh-Hant", "zh-Hans", "zh", "en"]
        chosen_lang = _find_best_lang(auto_subs, auto_priority)
        use_auto = True

    if chosen_lang is None:
        raise RuntimeError(
            "No subtitles found for this video (tried manual and auto-generated "
            f"in languages: {', '.join(LANGUAGE_PRIORITY)})"
        )

    print(f"Found {'auto' if use_auto else 'manual'} subtitles: {chosen_lang}", file=sys.stderr)

    # Get the VTT URL directly from the info dict
    subs_dict = auto_subs if use_auto else manual_subs
    formats = subs_dict[chosen_lang]
    vtt_url = None
    for fmt in formats:
        if fmt.get("ext") == "vtt":
            vtt_url = fmt["url"]
            break
    if vtt_url is None:
        # Fallback: use first available format URL
        vtt_url = formats[0]["url"]

    # Download VTT directly via urllib (avoids yt-dlp's download pipeline)
    vtt_path = Path(tmp_dir) / f"sub.{chosen_lang}.vtt"
    urllib.request.urlretrieve(vtt_url, vtt_path)

    if vtt_path.exists() and vtt_path.stat().st_size > 0:
        return vtt_path

    raise RuntimeError(f"Subtitle file for '{chosen_lang}' was empty.")


def _strip_vtt_tags(text: str) -> str:
    """Remove VTT inline tags like <c>, <00:01:02.345>, alignment, etc."""
    return re.sub(r"<[^>]+>", "", text).strip()


def parse_vtt(file_path: Path) -> list[dict]:
    """Parse a VTT file into a list of {start, text} segments.

    Handles YouTube's rolling-window auto-caption format where each cue
    contains two lines: the first repeats the previous cue's text, and
    the second contains the new content. We take only the last text line
    of each cue to avoid duplication.
    """
    content = file_path.read_text(encoding="utf-8")
    # Split into cue blocks separated by blank lines
    blocks = re.split(r"\n\n+", content)

    timestamp_re = re.compile(
        r"(\d{2}):(\d{2}):(\d{2})\.(\d{3})\s*-->\s*\d{2}:\d{2}:\d{2}\.\d{3}"
    )

    segments = []
    for block in blocks:
        lines = block.strip().split("\n")
        # Find the timestamp line
        start_time = None
        text_lines = []
        for line in lines:
            match = timestamp_re.search(line)
            if match:
                h, m, s, ms = int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4))
                start_time = h * 3600 + m * 60 + s + ms / 1000
            elif start_time is not None and not line.strip().isdigit():
                cleaned = _strip_vtt_tags(line)
                if cleaned:
                    text_lines.append(cleaned)

        if start_time is not None and text_lines:
            # For rolling-window format: take only the LAST line (new content)
            # For normal format: take all lines joined
            # Detect rolling-window: if there are exactly 2 text lines and
            # the first one matches a previous segment's text, take only the last
            if len(text_lines) == 2 and segments and text_lines[0] == segments[-1].get("_full", ""):
                text = text_lines[-1]
            else:
                text = " ".join(text_lines)

            if text:
                segments.append({"start": start_time, "text": text, "_full": " ".join(text_lines)})

    # Remove helper field and deduplicate consecutive identical texts
    deduped = []
    for seg in segments:
        seg.pop("_full", None)
        if not deduped or seg["text"] != deduped[-1]["text"]:
            deduped.append(seg)

    return deduped


def merge_segments(segments: list[dict]) -> list[dict]:
    """Merge segments into paragraphs based on time gaps."""
    if not segments:
        return []

    paragraphs = []
    current_start = segments[0]["start"]
    current_texts = [segments[0]["text"]]
    current_end = segments[0]["start"]

    for seg in segments[1:]:
        gap = seg["start"] - current_end
        elapsed = seg["start"] - current_start

        if gap > 5.0 or elapsed > 60.0:
            # Flush current paragraph
            merged_text = _merge_texts(current_texts)
            if merged_text:
                paragraphs.append({"start": current_start, "text": merged_text})
            current_start = seg["start"]
            current_texts = [seg["text"]]
        else:
            current_texts.append(seg["text"])

        current_end = seg["start"]

    # Flush last paragraph
    merged_text = _merge_texts(current_texts)
    if merged_text:
        paragraphs.append({"start": current_start, "text": merged_text})

    return paragraphs


def _merge_texts(texts: list[str]) -> str:
    """Join texts, removing duplicate adjacent sentences."""
    deduped = []
    for t in texts:
        if not deduped or t != deduped[-1]:
            deduped.append(t)
    return " ".join(deduped)


def format_timestamp(seconds: float) -> str:
    """Format seconds into [HH:MM:SS] or [MM:SS]."""
    total = int(seconds)
    h, remainder = divmod(total, 3600)
    m, s = divmod(remainder, 60)
    if h > 0:
        return f"[{h:02d}:{m:02d}:{s:02d}]"
    return f"[{m:02d}:{s:02d}]"


def format_duration(seconds: int) -> str:
    """Format duration as H:MM:SS or MM:SS."""
    h, remainder = divmod(seconds, 3600)
    m, s = divmod(remainder, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def format_upload_date(date_str: str) -> str:
    """Format YYYYMMDD to YYYY-MM-DD."""
    if len(date_str) == 8:
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    return date_str


def format_markdown(info: dict, paragraphs: list[dict]) -> str:
    """Build the final Markdown document."""
    lines = [
        f"# {info['title']}",
        "",
        f"- 頻道：{info['channel']}",
        f"- 日期：{format_upload_date(info['upload_date'])}",
        f"- 連結：{info['webpage_url']}",
        f"- 時長：{format_duration(info['duration'])}",
        "",
        "---",
        "",
        "## Transcript",
        "",
    ]

    for para in paragraphs:
        ts = format_timestamp(para["start"])
        lines.append(f"**{ts}** {para['text']}")
        lines.append("")

    return "\n".join(lines)


def sanitize_filename(name: str) -> str:
    """Remove special characters, replace spaces with underscores, truncate."""
    # Normalize unicode
    name = unicodedata.normalize("NFKC", name)
    # Remove characters that are problematic in filenames
    name = re.sub(r'[\\/:*?"<>|]', "", name)
    # Replace spaces and consecutive underscores
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"_+", "_", name)
    name = name.strip("_.")
    # Truncate to reasonable length
    if len(name) > 80:
        name = name[:80].rstrip("_")
    return name


def save_transcript(content: str, info: dict) -> Path:
    """Save Markdown to ~/transcripts/{YYYY-MM}/{channel}_{title}.md."""
    date_str = info.get("upload_date", "")
    if len(date_str) >= 6:
        folder_name = f"{date_str[:4]}-{date_str[4:6]}"
    else:
        folder_name = "unknown"

    channel = sanitize_filename(info["channel"])
    title = sanitize_filename(info["title"])
    filename = f"{channel}_{title}.md"

    out_dir = Path.home() / "transcripts" / folder_name
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / filename
    out_path.write_text(content, encoding="utf-8")
    return out_path


def main():
    if len(sys.argv) < 2:
        print("Usage: transcript.py <youtube_url>", file=sys.stderr)
        sys.exit(1)

    url = sys.argv[1]

    try:
        print("Fetching video info...", file=sys.stderr)
        raw_info = extract_info(url)
        info = get_video_info(raw_info, url)

        with tempfile.TemporaryDirectory() as tmp_dir:
            print("Downloading subtitles...", file=sys.stderr)
            vtt_path = download_subtitles(url, tmp_dir, raw_info)

            print("Parsing subtitles...", file=sys.stderr)
            segments = parse_vtt(vtt_path)

            if not segments:
                print("Error: Subtitle file was empty or could not be parsed.", file=sys.stderr)
                sys.exit(1)

            print("Merging segments...", file=sys.stderr)
            paragraphs = merge_segments(segments)

        content = format_markdown(info, paragraphs)
        out_path = save_transcript(content, info)
        print(str(out_path))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
