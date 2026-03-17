"""Download YouTube subtitles and format them into clean Markdown."""

import argparse
import json
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

DEFAULT_API = "anthropic"
DEFAULT_MODEL = {
    "anthropic": "claude-haiku-4-5-20251001",
    "openai": "gpt-4o-mini",
    "gemini": "gemini-2.0-flash",
    "grok": "grok-3-mini-fast",
}
# OpenAI-compatible providers: (base_url, env_var for API key)
OPENAI_COMPAT = {
    "openai": (None, "OPENAI_API_KEY"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai/", "GEMINI_API_KEY"),
    "grok": ("https://api.x.ai/v1", "XAI_API_KEY"),
}
BATCH_SIZE = 10

TRANSLATE_PROMPT = """\
You are a professional translator. Translate each English paragraph into Traditional Chinese (繁體中文).
Return a JSON array of strings, one translation per input paragraph, in the same order.
Do NOT include the original English. Only return the JSON array, no other text.

Paragraphs to translate:
"""

PENDING_DIR = Path.home() / "transcripts" / ".pending"


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
            f"in languages: {', '.join(MANUAL_LANG_PRIORITY + AUTO_LANG_PRIORITY)})"
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
    """Build the final Markdown document.

    If paragraphs have a 'translation' field, output bilingual format.
    """
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
        if "translation" in para:
            lines.append(f"> {para['translation']}")
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


# ---------------------------------------------------------------------------
# Translation (Phase 2)
# ---------------------------------------------------------------------------

def _call_llm(api: str, model: str, prompt: str) -> str:
    """Call an LLM API and return the text response."""
    if api == "anthropic":
        import anthropic
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=model,
            max_tokens=8192,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    elif api in OPENAI_COMPAT:
        import os
        import openai
        base_url, env_var = OPENAI_COMPAT[api]
        api_key = os.environ.get(env_var)
        if not api_key:
            raise RuntimeError(f"Missing {env_var} environment variable for --api {api}")
        client = openai.OpenAI(api_key=api_key, base_url=base_url)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content.strip()
    else:
        raise RuntimeError(f"Unsupported API: {api}")


def _parse_translation_response(raw: str) -> list[str]:
    """Extract JSON array from LLM response text."""
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
        raw = raw.strip()
    # Find the outermost JSON array
    start = raw.find("[")
    end = raw.rfind("]")
    if start != -1 and end != -1 and end > start:
        return json.loads(raw[start:end + 1])
    raise RuntimeError(f"Failed to parse translation response: {raw[:200]}")


def translate_paragraphs(paragraphs: list[dict], api: str, model: str) -> list[dict]:
    """Translate paragraphs using the specified API and model.

    Sends paragraphs in batches of BATCH_SIZE, returns paragraphs with
    'translation' field added.
    """
    result = []

    batches = [paragraphs[i:i + BATCH_SIZE] for i in range(0, len(paragraphs), BATCH_SIZE)]
    total = len(batches)

    for idx, batch in enumerate(batches, 1):
        print(f"Translating batch {idx}/{total} ({api}/{model})...", file=sys.stderr)
        texts = [p["text"] for p in batch]
        prompt = TRANSLATE_PROMPT + json.dumps(texts, ensure_ascii=False)

        raw = _call_llm(api, model, prompt)
        translations = _parse_translation_response(raw)

        if len(translations) != len(batch):
            print(
                f"Warning: expected {len(batch)} translations, got {len(translations)}",
                file=sys.stderr,
            )

        for i, para in enumerate(batch):
            enriched = dict(para)
            if i < len(translations):
                enriched["translation"] = translations[i]
            result.append(enriched)

    return result


def submit_batch_translation(paragraphs: list[dict], info: dict, model: str) -> str:
    """Submit a Message Batch for translation (Anthropic only), return batch_id."""
    import anthropic
    client = anthropic.Anthropic()

    batches = [paragraphs[i:i + BATCH_SIZE] for i in range(0, len(paragraphs), BATCH_SIZE)]
    requests = []

    for idx, batch in enumerate(batches):
        texts = [p["text"] for p in batch]
        prompt = TRANSLATE_PROMPT + json.dumps(texts, ensure_ascii=False)
        requests.append({
            "custom_id": f"batch-{idx}",
            "params": {
                "model": model,
                "max_tokens": 4096,
                "messages": [{"role": "user", "content": prompt}],
            },
        })

    print(f"Submitting batch with {len(requests)} request(s)...", file=sys.stderr)
    batch_resp = client.messages.batches.create(requests=requests)
    batch_id = batch_resp.id

    # Save pending data for later retrieval
    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    pending_path = PENDING_DIR / f"{batch_id}.json"
    pending_data = {
        "info": info,
        "paragraphs": paragraphs,
        "batch_count": len(batches),
    }
    pending_path.write_text(json.dumps(pending_data, ensure_ascii=False), encoding="utf-8")

    return batch_id


def fetch_batch_result(batch_id: str) -> None:
    """Fetch batch results, assemble translated Markdown, and save."""
    client = _get_anthropic_client()

    # Load pending data
    pending_path = PENDING_DIR / f"{batch_id}.json"
    if not pending_path.exists():
        raise RuntimeError(f"No pending data found for batch {batch_id}")

    pending_data = json.loads(pending_path.read_text(encoding="utf-8"))
    info = pending_data["info"]
    paragraphs = pending_data["paragraphs"]

    # Check batch status
    batch_status = client.messages.batches.retrieve(batch_id)
    if batch_status.processing_status != "ended":
        print(
            f"Batch is still processing (status: {batch_status.processing_status}). "
            "Please try again later.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Collect translations keyed by custom_id
    translation_map: dict[str, list[str]] = {}
    for result in client.messages.batches.results(batch_id):
        custom_id = result.custom_id
        if result.result.type == "succeeded":
            raw = result.result.message.content[0].text.strip()
            try:
                translation_map[custom_id] = _parse_translation_response(raw)
            except RuntimeError:
                print(f"Warning: could not parse response for {custom_id}", file=sys.stderr)
        else:
            print(f"Warning: {custom_id} failed: {result.result.type}", file=sys.stderr)

    # Apply translations to paragraphs
    batches = [paragraphs[i:i + BATCH_SIZE] for i in range(0, len(paragraphs), BATCH_SIZE)]
    enriched = []
    for idx, batch in enumerate(batches):
        translations = translation_map.get(f"batch-{idx}", [])
        for i, para in enumerate(batch):
            p = dict(para)
            if i < len(translations):
                p["translation"] = translations[i]
            enriched.append(p)

    content = format_markdown(info, enriched)
    out_path = save_transcript(content, info)
    print(str(out_path))

    # Clean up pending file
    pending_path.unlink(missing_ok=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download YouTube transcripts")
    parser.add_argument("url", nargs="?", help="YouTube video URL")
    parser.add_argument("--translate", action="store_true", help="Translate English transcript to Chinese")
    parser.add_argument(
        "--api",
        choices=list(DEFAULT_MODEL.keys()),
        default=DEFAULT_API,
        help=f"API provider for translation (default: {DEFAULT_API})",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model name for translation (default depends on --api)",
    )
    parser.add_argument("--batch", action="store_true", help="Use Anthropic Batch API for translation (with --translate)")
    parser.add_argument("--fetch", metavar="BATCH_ID", help="Fetch results of a previous batch translation")
    return parser.parse_args()


def main():
    args = parse_args()

    # --fetch mode: retrieve batch results
    if args.fetch:
        try:
            fetch_batch_result(args.fetch)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        return

    if not args.url:
        print("Error: URL is required (unless using --fetch)", file=sys.stderr)
        sys.exit(1)

    try:
        print("Fetching video info...", file=sys.stderr)
        raw_info = extract_info(args.url)
        info = get_video_info(raw_info, args.url)

        with tempfile.TemporaryDirectory() as tmp_dir:
            print("Downloading subtitles...", file=sys.stderr)
            vtt_path = download_subtitles(args.url, tmp_dir, raw_info)

            print("Parsing subtitles...", file=sys.stderr)
            segments = parse_vtt(vtt_path)

            if not segments:
                print("Error: Subtitle file was empty or could not be parsed.", file=sys.stderr)
                sys.exit(1)

            print("Merging segments...", file=sys.stderr)
            paragraphs = merge_segments(segments)

        if args.translate:
            api = args.api
            model = args.model or DEFAULT_MODEL[api]
            if args.batch:
                if api != "anthropic":
                    print("Error: --batch is only supported with --api anthropic", file=sys.stderr)
                    sys.exit(1)
                batch_id = submit_batch_translation(paragraphs, info, model)
                print(f"Batch submitted: {batch_id}", file=sys.stderr)
                print(f"Run with --fetch {batch_id} to retrieve results.", file=sys.stderr)
                return
            else:
                paragraphs = translate_paragraphs(paragraphs, api, model)

        content = format_markdown(info, paragraphs)
        out_path = save_transcript(content, info)
        print(str(out_path))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
