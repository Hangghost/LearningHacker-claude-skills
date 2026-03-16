# YouTube 逐字稿自動化工具 - 實作計劃

## 目標

將 YouTube 影片的逐字稿處理流程自動化：
**下載字幕 → 清理整理 → 輸出 Markdown**

## 使用方式（完成後）

```bash
/transcript https://youtube.com/watch?v=xxx
/transcript https://youtube.com/watch?v=xxx --translate  # Phase 2: 英文加中文對照
```

## 輸出格式

存檔路徑：`~/transcripts/{YYYY-MM}/{channel}_{title}.md`

```markdown
# 影片標題

- 頻道：@channel_name
- 日期：2026-03-15
- 連結：https://youtube.com/watch?v=xxx
- 時長：1:23:45

---

## Transcript

**[00:00]** 開場段落內容，已合併短句、去除重複贅字，
每個段落保留起始時間戳。

**[02:15]** 第二段內容繼續在這裡...
```

## 實作範圍

### Phase 1：零 AI 成本版（優先完成）

- [ ] `transcript.py` - 核心腳本
  - `download_subtitles(url)` - 用 yt-dlp 下載字幕（.vtt / .srt）
  - `parse_subtitles(file)` - 解析時間戳 + 文字
  - `clean_transcript(segments)` - 去重複、合併短句成段落
  - `format_markdown(data)` - 輸出格式化 Markdown
  - `save_file(content, metadata)` - 存到 ~/transcripts/
- [ ] `skill.md` - Claude Code Skill 定義

### Phase 2：英文翻譯（之後再加）

- [ ] 接 Anthropic API（Haiku 模型）
- [ ] Batch API 支援（省 50% 費用）
- [ ] `--translate` flag 觸發中英對照輸出

## 技術選擇

| 元件 | 工具 | 原因 |
|------|------|------|
| 字幕下載 | `yt-dlp` | 最穩定、支援最廣 |
| 字幕解析 | Python 內建 | .vtt/.srt 格式不複雜 |
| 清理邏輯 | 規則處理 | 不需 AI，零成本 |
| 翻譯 | Claude Haiku API | Phase 2，~$0.04/hr 影片 |
| 輸出 | Markdown | 方便 AI 閱讀、本地搜尋 |

## 依賴

```
yt-dlp
```

Phase 2 額外需要：
```
anthropic
```

## 費用估算

| 情境 | 成本 |
|------|------|
| 中文影片（Phase 1）| $0 |
| 英文影片不翻譯（Phase 1）| $0 |
| 英文影片翻譯 Haiku 即時（Phase 2）| ~$0.08/hr |
| 英文影片翻譯 Haiku Batch（Phase 2）| ~$0.04/hr |
| 每月 20 支 1hr 英文影片 Batch | ~$0.80/月 |

## 待決定

- [ ] 確認 `~/transcripts/` 作為預設存檔路徑是否合適
- [ ] 段落合併的規則：每 N 秒切一段？還是依停頓/句號切？
- [ ] 是否要支援播放清單（playlist）批次處理
