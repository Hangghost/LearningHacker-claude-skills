# Changelog

All notable changes to skills in this repository will be documented in this file.
Format: each entry is grouped by date, then by skill name and version.

## 2026-03-17

### release v1.0.0
- 初始版本：自動化 skill 發版流程（版本號更新、CHANGELOG、commit、tag）

### distill v1.0.0
- 新增 distill skill：從訪談／Podcast 逐字稿萃取結構化寫作素材
- 英文逐字稿自動產出繁體中文翻譯版

### yt-transcript v1.2.0
- 支援多 LLM 翻譯 API（OpenAI、Gemini、Grok），可透過 `--api` 參數切換
- 支援指定模型 `--model`
- 新增 Anthropic Batch API 支援（`--batch` / `--fetch`）

### yt-transcript v1.1.0
- 新增 `--translate` 即時翻譯功能（英→中，預設使用 Claude Haiku）

### yt-transcript v1.0.0
- 初始版本：下載 YouTube 字幕，輸出結構化 Markdown
- 字幕優先序：手動 zh → en，自動 en → zh
- 儲存至 `~/transcripts/{YYYY-MM}/`
