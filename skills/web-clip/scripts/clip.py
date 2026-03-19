"""Clip web articles into Markdown + images for blog reference."""

import argparse
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
import trafilatura
from bs4 import BeautifulSoup

DEFAULT_API = "anthropic"
DEFAULT_MODEL = {
    "anthropic": "claude-haiku-4-5-20251001",
    "openai": "gpt-4o-mini",
    "gemini": "gemini-2.0-flash",
    "grok": "grok-3-mini-fast",
}
OPENAI_COMPAT = {
    "openai": (None, "OPENAI_API_KEY"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai/", "GEMINI_API_KEY"),
    "grok": ("https://api.x.ai/v1", "XAI_API_KEY"),
}
BATCH_SIZE = 10
DEFAULT_OUTPUT_DIR = Path.home() / "Documents" / "Procjects" / "00_work_space" / "brain" / "clips"

TRANSLATE_PROMPT = """\
You are a professional translator. Translate the following Markdown content from English to Traditional Chinese (繁體中文).
Preserve all Markdown formatting, including headings, links, bold, italic, lists, code blocks, and image references.
Do NOT translate code, URLs, or image paths. Only translate the prose text.
Return ONLY the translated Markdown, no other text.

Content to translate:
"""

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,zh-TW;q=0.8",
}


# ---------------------------------------------------------------------------
# X/Twitter support via FixTweet API
# ---------------------------------------------------------------------------

def is_x_url(url: str) -> bool:
    """Check if URL is an X/Twitter tweet URL."""
    parsed = urlparse(url)
    return parsed.netloc in (
        "x.com", "www.x.com", "twitter.com", "www.twitter.com",
    ) and "/status/" in parsed.path


def _parse_x_url(url: str) -> tuple[str, str]:
    """Extract (screen_name, tweet_id) from X URL."""
    parsed = urlparse(url)
    parts = parsed.path.strip("/").split("/")
    # format: /<screen_name>/status/<tweet_id>
    screen_name = parts[0]
    tweet_id = parts[2]
    return screen_name, tweet_id


def fetch_x_tweet(url: str) -> dict:
    """Fetch tweet data from FixTweet API and return article dict."""
    screen_name, tweet_id = _parse_x_url(url)
    api_url = f"https://api.fxtwitter.com/{screen_name}/status/{tweet_id}"

    with httpx.Client(follow_redirects=True, timeout=30, headers=HEADERS) as client:
        resp = client.get(api_url)
        resp.raise_for_status()
        data = resp.json()

    tweet = data.get("tweet", {})
    author_info = tweet.get("author", {})
    author_name = author_info.get("name", "")
    screen = author_info.get("screen_name", "")
    author = f"{author_name} (@{screen})" if author_name else screen

    # Extract date
    created = tweet.get("created_at", "")
    date = ""
    if created:
        try:
            from datetime import datetime as dt
            parsed_dt = dt.strptime(created, "%a %b %d %H:%M:%S %z %Y")
            date = parsed_dt.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            date = created[:10] if len(created) >= 10 else created

    article = tweet.get("article")
    if article and article.get("content"):
        # X Article (long-form) — convert Draft.js blocks to markdown
        title = article.get("title", "")
        entity_map = article["content"].get("entityMap", [])
        # Build entity lookup: key (str) -> entity value
        entities = {}
        for item in entity_map:
            entities[str(item["key"])] = item["value"]
        content = _draftjs_to_markdown(article["content"]["blocks"], entities)
        # Collect media image URLs from article
        media_entities = article.get("media_entities", [])
        image_urls = []
        for me in media_entities:
            img_url = me.get("media_info", {}).get("original_img_url", "")
            if img_url:
                image_urls.append(img_url)
    else:
        # Regular tweet — use tweet text
        title = ""
        raw_text = tweet.get("text", "")
        content = raw_text
        image_urls = []
        # Check for media in the tweet itself
        media = tweet.get("media", {})
        if media:
            photos = media.get("photos", [])
            for photo in photos:
                img_url = photo.get("url", "")
                if img_url:
                    image_urls.append(img_url)

    if not title:
        # Use first line of content as title, truncated
        first_line = content.split("\n")[0][:80]
        title = f"@{screen}: {first_line}" if first_line else f"@{screen} tweet"

    return {
        "title": title,
        "author": author,
        "date": date,
        "content": content,
        "image_urls": image_urls,
    }


def _draftjs_to_markdown(blocks: list[dict], entities: dict) -> str:
    """Convert Draft.js content blocks to Markdown."""
    lines = []
    prev_type = None

    for block in blocks:
        btype = block.get("type", "unstyled")
        text = block.get("text", "")
        inline_styles = block.get("inlineStyleRanges", [])
        entity_ranges = block.get("entityRanges", [])

        # Skip atomic blocks (media embeds) — images handled separately
        if btype == "atomic":
            continue

        # Apply inline styles and entity links
        text = _apply_inline_formatting(text, inline_styles, entity_ranges, entities)

        if btype == "header-one":
            # Add blank line before h1 if previous wasn't empty
            if prev_type and prev_type != "header-one":
                lines.append("")
            lines.append(f"# {text}")
        elif btype == "header-two":
            if prev_type and prev_type != "header-one":
                lines.append("")
            lines.append(f"## {text}")
        elif btype == "header-three":
            if prev_type:
                lines.append("")
            lines.append(f"### {text}")
        elif btype == "unordered-list-item":
            lines.append(f"- {text}")
        elif btype == "ordered-list-item":
            lines.append(f"1. {text}")
        elif btype == "blockquote":
            lines.append(f"> {text}")
        elif btype == "code-block":
            lines.append(f"```\n{text}\n```")
        else:
            # unstyled — regular paragraph
            if text.strip():
                lines.append(text)
            else:
                lines.append("")

        prev_type = btype

    # Clean up multiple blank lines
    result = "\n\n".join(lines)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


def _apply_inline_formatting(
    text: str,
    inline_styles: list[dict],
    entity_ranges: list[dict],
    entities: dict,
) -> str:
    """Apply bold/italic styles and links to text via character-level markers."""
    if not text or (not inline_styles and not entity_ranges):
        return text

    n = len(text)
    # Track per-character: bold, italic, link_url
    bold = [False] * n
    italic = [False] * n
    link = [None] * n  # url or None

    for style in inline_styles:
        start = style["offset"]
        end = min(start + style["length"], n)
        style_name = style.get("style", "")
        for i in range(start, end):
            if style_name == "Bold":
                bold[i] = True
            elif style_name == "Italic":
                italic[i] = True

    for er in entity_ranges:
        key = str(er["key"])
        entity = entities.get(key)
        if not entity:
            continue
        if entity.get("type") == "LINK":
            url = entity.get("data", {}).get("url", "")
            if url:
                start = er["offset"]
                end = min(start + er["length"], n)
                for i in range(start, end):
                    link[i] = url

    # Build output by grouping consecutive chars with same formatting
    result = []
    i = 0
    while i < n:
        cur_bold = bold[i]
        cur_italic = italic[i]
        cur_link = link[i]

        # Find span of same formatting
        j = i
        while j < n and bold[j] == cur_bold and italic[j] == cur_italic and link[j] == cur_link:
            j += 1

        span = text[i:j]

        if cur_bold and cur_italic:
            span = f"***{span}***"
        elif cur_bold:
            span = f"**{span}**"
        elif cur_italic:
            span = f"*{span}*"

        if cur_link:
            span = f"[{span}]({cur_link})"

        result.append(span)
        i = j

    return "".join(result)


# ---------------------------------------------------------------------------
# Step 1 & 2: Fetch and extract
# ---------------------------------------------------------------------------

def fetch_html(url: str) -> str:
    """Fetch HTML from URL using httpx."""
    with httpx.Client(follow_redirects=True, timeout=30, headers=HEADERS) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.text


def extract_article(html: str, url: str) -> dict:
    """Extract article content and metadata using trafilatura."""
    metadata = trafilatura.extract_metadata(html, default_url=url)

    # Try trafilatura markdown output
    content = trafilatura.extract(
        html,
        output_format="markdown",
        include_images=True,
        include_links=True,
        favor_recall=True,
    )

    if not content or len(content.strip()) < 100:
        # Fallback: try with different settings
        content = trafilatura.extract(
            html,
            output_format="markdown",
            include_images=True,
            include_links=True,
            favor_precision=False,
            favor_recall=True,
            no_fallback=False,
        )

    if not content:
        raise RuntimeError("Could not extract article content from this URL.")

    title = ""
    author = ""
    date = ""
    if metadata:
        title = metadata.title or ""
        author = metadata.author or ""
        date = metadata.date or ""

    return {
        "title": title,
        "author": author,
        "date": date,
        "content": content,
    }


# ---------------------------------------------------------------------------
# Step 3 & 4: Images
# ---------------------------------------------------------------------------

def extract_markdown_images(markdown: str) -> list[str]:
    """Extract image paths from markdown ![alt](path) syntax."""
    return re.findall(r"!\[[^\]]*\]\(([^)]+)\)", markdown)


def _guess_extension(url: str, content_type: str = "") -> str:
    """Guess file extension from URL or content-type."""
    # Try from URL path
    path = urlparse(url).path
    ext = Path(path).suffix.lower()
    if ext in (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".avif", ".bmp"):
        return ext

    # Try from content-type
    ct = content_type.lower()
    if "png" in ct:
        return ".png"
    if "jpeg" in ct or "jpg" in ct:
        return ".jpg"
    if "gif" in ct:
        return ".gif"
    if "svg" in ct:
        return ".svg"
    if "webp" in ct:
        return ".webp"

    return ".png"  # default


def download_images(
    md_image_paths: list[str], base_url: str, images_dir: Path
) -> dict[str, str]:
    """Download images and return mapping from markdown path to local filename.

    md_image_paths: paths as they appear in the markdown (may be relative or absolute).
    base_url: the article URL, used to resolve relative paths.
    """
    images_dir.mkdir(parents=True, exist_ok=True)
    path_to_local: dict[str, str] = {}

    with httpx.Client(follow_redirects=True, timeout=30, headers=HEADERS) as client:
        for i, md_path in enumerate(md_image_paths, 1):
            # Resolve to absolute URL for downloading
            abs_url = urljoin(base_url, md_path)
            try:
                resp = client.get(abs_url)
                resp.raise_for_status()
                content_type = resp.headers.get("content-type", "")
                ext = _guess_extension(abs_url, content_type)
                filename = f"{i:03d}{ext}"
                filepath = images_dir / filename
                filepath.write_bytes(resp.content)
                path_to_local[md_path] = filename
                print(f"  Downloaded image {i}/{len(md_image_paths)}: {filename}", file=sys.stderr)
            except Exception as e:
                print(f"  Warning: failed to download {abs_url}: {e}", file=sys.stderr)

    return path_to_local


def replace_image_paths(markdown: str, path_to_local: dict[str, str]) -> str:
    """Replace image paths in markdown with relative local paths."""
    for original_path, local_name in path_to_local.items():
        escaped = re.escape(original_path)
        markdown = re.sub(escaped, f"images/{local_name}", markdown)
    return markdown


# ---------------------------------------------------------------------------
# Step 5: Output
# ---------------------------------------------------------------------------

def sanitize_slug(text: str) -> str:
    """Create a filesystem-safe slug from text."""
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r'[\\/:*?"<>|]', "", text)
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"_+", "_", text)
    text = text.strip("_.")
    if len(text) > 60:
        text = text[:60].rstrip("_")
    return text


def build_frontmatter(title: str, source: str, author: str, date: str) -> str:
    """Build YAML frontmatter."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = ["---"]
    lines.append(f'title: "{title}"')
    lines.append(f'source: "{source}"')
    if author:
        lines.append(f'author: "{author}"')
    if date:
        lines.append(f'date: "{date}"')
    lines.append(f'clipped: "{today}"')
    lines.append("---")
    return "\n".join(lines)


def save_clip(
    content: str,
    url: str,
    article: dict,
    path_to_local: dict[str, str],
    translated_content: str | None = None,
    output_dir: Path | None = None,
) -> Path:
    """Save clipped article to {output_dir}/YYYY-MM/{domain}_{slug}/."""
    today = datetime.now(timezone.utc)
    folder_month = today.strftime("%Y-%m")

    domain = urlparse(url).netloc.replace("www.", "")
    slug = sanitize_slug(article["title"]) if article["title"] else "untitled"
    dir_name = f"{sanitize_slug(domain)}_{slug}"

    base = output_dir or DEFAULT_OUTPUT_DIR
    out_dir = base / folder_month / dir_name
    out_dir.mkdir(parents=True, exist_ok=True)

    frontmatter = build_frontmatter(
        article["title"], url, article["author"], article["date"]
    )

    # Replace image paths with relative local paths
    final_content = replace_image_paths(content, path_to_local)

    # Save index.md
    index_md = f"{frontmatter}\n\n{final_content}\n"
    (out_dir / "index.md").write_text(index_md, encoding="utf-8")

    # Save index_zh.md if translated
    if translated_content:
        final_zh = replace_image_paths(translated_content, path_to_local)
        zh_md = f"{frontmatter}\n\n{final_zh}\n"
        (out_dir / "index_zh.md").write_text(zh_md, encoding="utf-8")

    return out_dir


# ---------------------------------------------------------------------------
# Translation (reusing yt-transcript patterns)
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


def _split_into_chunks(markdown: str, max_chars: int = 50000) -> list[str]:
    """Split markdown into chunks by paragraphs, respecting max size."""
    paragraphs = re.split(r"\n\n+", markdown)
    chunks = []
    current = []
    current_len = 0

    for para in paragraphs:
        if current_len + len(para) > max_chars and current:
            chunks.append("\n\n".join(current))
            current = [para]
            current_len = len(para)
        else:
            current.append(para)
            current_len += len(para)

    if current:
        chunks.append("\n\n".join(current))

    return chunks


def translate_content(content: str, api: str, model: str) -> str:
    """Translate markdown content to Traditional Chinese."""
    chunks = _split_into_chunks(content)
    translated_chunks = []

    for i, chunk in enumerate(chunks, 1):
        print(f"Translating chunk {i}/{len(chunks)} ({api}/{model})...", file=sys.stderr)
        prompt = TRANSLATE_PROMPT + chunk
        result = _call_llm(api, model, prompt)
        translated_chunks.append(result)

    return "\n\n".join(translated_chunks)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clip web articles into Markdown + images")
    parser.add_argument("url", help="Article URL to clip")
    parser.add_argument("--translate", action="store_true", help="Translate to Traditional Chinese")
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
    parser.add_argument(
        "--output-dir",
        default=None,
        help=f"Output base directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    output_dir = Path(args.output_dir) if args.output_dir else DEFAULT_OUTPUT_DIR

    try:
        if is_x_url(args.url):
            # X/Twitter path
            print("Fetching tweet via FixTweet API...", file=sys.stderr)
            article = fetch_x_tweet(args.url)
            print(f"Title: {article['title']}", file=sys.stderr)

            # X tweets have direct image URLs, not embedded in markdown
            image_urls = article.pop("image_urls", [])

            # Create output dir for images
            today = datetime.now(timezone.utc)
            folder_month = today.strftime("%Y-%m")
            domain = urlparse(args.url).netloc.replace("www.", "")
            slug = sanitize_slug(article["title"]) if article["title"] else "untitled"
            dir_name = f"{sanitize_slug(domain)}_{slug}"
            out_dir = output_dir / folder_month / dir_name
            images_dir = out_dir / "images"

            path_to_local = {}
            if image_urls:
                print(f"Downloading {len(image_urls)} images...", file=sys.stderr)
                images_dir.mkdir(parents=True, exist_ok=True)
                with httpx.Client(follow_redirects=True, timeout=30, headers=HEADERS) as client:
                    for i, img_url in enumerate(image_urls, 1):
                        try:
                            resp = client.get(img_url)
                            resp.raise_for_status()
                            content_type = resp.headers.get("content-type", "")
                            ext = _guess_extension(img_url, content_type)
                            filename = f"{i:03d}{ext}"
                            (images_dir / filename).write_bytes(resp.content)
                            path_to_local[img_url] = filename
                            print(f"  Downloaded image {i}/{len(image_urls)}: {filename}", file=sys.stderr)
                            # Append image to content
                            article["content"] += f"\n\n![image {i}]({img_url})"
                        except Exception as e:
                            print(f"  Warning: failed to download {img_url}: {e}", file=sys.stderr)
        else:
            # Standard web article path
            print("Fetching page...", file=sys.stderr)
            html = fetch_html(args.url)

            print("Extracting article content...", file=sys.stderr)
            article = extract_article(html, args.url)
            print(f"Title: {article['title']}", file=sys.stderr)

            # Extract and download images
            md_image_paths = extract_markdown_images(article["content"])
            print(f"Found {len(md_image_paths)} images in article", file=sys.stderr)

            today = datetime.now(timezone.utc)
            folder_month = today.strftime("%Y-%m")
            domain = urlparse(args.url).netloc.replace("www.", "")
            slug = sanitize_slug(article["title"]) if article["title"] else "untitled"
            dir_name = f"{sanitize_slug(domain)}_{slug}"
            out_dir = output_dir / folder_month / dir_name
            images_dir = out_dir / "images"

            path_to_local = {}
            if md_image_paths:
                print("Downloading images...", file=sys.stderr)
                path_to_local = download_images(md_image_paths, args.url, images_dir)

        # Step 4: Translate (optional)
        translated_content = None
        if args.translate:
            api = args.api
            model = args.model or DEFAULT_MODEL[api]
            translated_content = translate_content(article["content"], api, model)

        # Step 5: Save
        print("Saving...", file=sys.stderr)
        out_dir = save_clip(
            article["content"],
            args.url,
            article,
            path_to_local,
            translated_content,
            output_dir=output_dir,
        )
        print(str(out_dir))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
