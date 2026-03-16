# YouTube 逐字稿工具 — Phase 1 實作計畫

## Context

建立第一個 Claude Code Skill：`/transcript <url>`，自動下載 YouTube 字幕、清理整理後輸出結構化 Markdown。Phase 1 零 AI 成本，純規則處理。使用 `uv` 管理 Python 環境與依賴。

## 檔案結構

```
yt-transcript/
├── PLAN.md              # 已存在
├── SKILL.md             # Skill 定義（Claude Code 入口）
├── pyproject.toml       # uv 專案配置 + 依賴
└── scripts/
    └── transcript.py    # 核心腳本
```

## 實作步驟

### Step 1: 建立 uv 專案結構

**`pyproject.toml`**
- `[project]` 宣告 `name = "yt-transcript"`, `python >= 3.10`
- `dependencies = ["yt-dlp"]`
- 不需要 CLI entry point，由 SKILL.md 指導 Claude 直接呼叫 `uv run python scripts/transcript.py <url>`

### Step 2: 實作 `scripts/transcript.py`

單一腳本，接受 YouTube URL 作為 `sys.argv[1]`，輸出存檔路徑。

#### 函式設計：

**`get_video_info(url) -> dict`**
- 用 `yt_dlp.YoutubeDL` 的 `extract_info(download=False)` 取得 metadata
- 回傳：`title`, `channel`, `upload_date`, `duration`, `webpage_url`

**`download_subtitles(url, tmp_dir) -> Path`**
- 用 yt-dlp 下載字幕到暫存目錄
- 語言偏好順序：`zh-Hant`, `zh-Hans`, `zh`, `en` → 手動字幕
- 手動字幕全部找不到時，fallback 到自動生成字幕（同樣語言順序）
- 輸出格式指定 `.vtt`
- 找不到任何字幕時 raise 明確錯誤訊息

**`parse_vtt(file_path) -> list[dict]`**
- 解析 .vtt 格式：跳過 header、解析時間戳與文字
- 回傳 `[{"start": float_seconds, "text": "..."}, ...]`
- 去除 HTML tag（`<c>`, `<b>` 等）
- 去除重複行（自動字幕常見的逐字重複）

**`merge_segments(segments) -> list[dict]`**
- 策略：**時間間隔切段**
  - 累積文字直到與下一段間隔 > 2 秒 **或** 累積超過 30 秒
  - 每段保留起始時間戳
  - 合併時去除完全重複的相鄰句子

**`format_markdown(info, paragraphs) -> str`**
- 輸出格式如 PLAN.md 定義的 Markdown
- 時長格式化為 `H:MM:SS` 或 `MM:SS`
- 時間戳格式化為 `[HH:MM:SS]` 或 `[MM:SS]`

**`save_transcript(content, info) -> Path`**
- 路徑：`~/transcripts/{YYYY-MM}/{channel}_{title}.md`
- 檔名清理：移除特殊字元，空格轉底線，截斷過長檔名
- 自動建立目錄（`mkdir -p`）
- 回傳存檔路徑

**`main()`**
- 接收 `sys.argv[1]` 作為 URL
- 用 `tempfile.TemporaryDirectory` 管理暫存檔
- 依序呼叫上述函式
- 成功時印出存檔路徑，失敗時印出錯誤訊息並 `sys.exit(1)`

### Step 3: 撰寫 SKILL.md

```yaml
---
name: transcript
description: >
  Download and format YouTube video transcripts into clean Markdown.
  Use when user invokes /transcript with a YouTube URL.
---
```

Body 指導 Claude：
1. 先確認 `yt-dlp` 可用（`uv run yt-dlp --version`）
2. 執行 `cd <skill_dir> && uv run python scripts/transcript.py <url>`
3. 成功後告知使用者存檔路徑
4. 失敗時顯示錯誤並建議排查方式

### Step 4: 初始化 uv 環境

```bash
cd yt-transcript && uv sync
```

## 驗證方式

1. `cd yt-transcript && uv run python scripts/transcript.py "https://www.youtube.com/watch?v=<test_video>"` — 確認產生正確的 Markdown 檔案
2. 檢查輸出檔案內容：metadata 正確、段落有時間戳、無重複行
3. 測試無字幕影片 — 確認錯誤訊息清楚
4. Symlink 到 `~/.claude/skills/` 後測試 `/transcript` 指令
