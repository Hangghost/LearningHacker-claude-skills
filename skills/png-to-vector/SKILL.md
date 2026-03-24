---
name: png-to-vector
version: 1.0.0
description: >
  Convert PNG images to vector formats (SVG and AI).
  Use when user invokes /png-to-vector with a file path.
---

# PNG to Vector Skill

## Usage

The user will provide a PNG file path. Convert the bitmap image to vector format (SVG and/or AI) using image tracing.

## Steps

1. **Ask output settings:** Use the `AskUserQuestion` tool to ask the user:
   - Question: "輸出設定？"
   - Option 1: "同目錄輸出 SVG + AI (Recommended)" — description: "輸出到與原圖相同的目錄，同時產生 .svg 和 .ai"
   - Option 2: "只要 SVG" — description: "只輸出 .svg 向量檔"
   - Option 3: "只要 AI" — description: "只輸出 .ai (Adobe Illustrator) 檔"
   - Option 4: "自訂路徑" — description: "輸入自訂的輸出資料夾路徑"

   Based on the user's choice, determine `--format` (`both`, `svg`, or `ai`) and optional `--output-dir`.

2. **Ask detail level:** Use the `AskUserQuestion` tool to ask the user:
   - Question: "向量化精細度？"
   - Option 1: "Medium (Recommended)" — description: "平衡細節與檔案大小"
   - Option 2: "High" — description: "保留更多細節，檔案較大"
   - Option 3: "Low" — description: "簡化細節，檔案較小，適合 icon/logo"

3. **Verify dependencies:**

   ```bash
   cd /Users/chenhunglun/Documents/Procjects/LearningHacker-claude-skills && DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib uv run python -c "import vtracer; import cairosvg"
   ```

   If this fails, run `cd /Users/chenhunglun/Documents/Procjects/LearningHacker-claude-skills && uv sync` first.
   If cairosvg fails with "no library called cairo", ensure `brew install cairo` has been run.

4. **Run the conversion script:**

   ```bash
   # Default: output both SVG + AI, medium detail
   cd /Users/chenhunglun/Documents/Procjects/LearningHacker-claude-skills && uv run python skills/png-to-vector/scripts/png_to_vector.py "<file_path>"

   # SVG only
   cd /Users/chenhunglun/Documents/Procjects/LearningHacker-claude-skills && uv run python skills/png-to-vector/scripts/png_to_vector.py "<file_path>" -f svg

   # AI only
   cd /Users/chenhunglun/Documents/Procjects/LearningHacker-claude-skills && uv run python skills/png-to-vector/scripts/png_to_vector.py "<file_path>" -f ai

   # High detail
   cd /Users/chenhunglun/Documents/Procjects/LearningHacker-claude-skills && uv run python skills/png-to-vector/scripts/png_to_vector.py "<file_path>" --detail high

   # Low detail (good for logos/icons)
   cd /Users/chenhunglun/Documents/Procjects/LearningHacker-claude-skills && uv run python skills/png-to-vector/scripts/png_to_vector.py "<file_path>" --detail low

   # Binary mode (black & white tracing)
   cd /Users/chenhunglun/Documents/Procjects/LearningHacker-claude-skills && uv run python skills/png-to-vector/scripts/png_to_vector.py "<file_path>" --colormode binary

   # Custom output directory
   cd /Users/chenhunglun/Documents/Procjects/LearningHacker-claude-skills && uv run python skills/png-to-vector/scripts/png_to_vector.py "<file_path>" -o "/path/to/output"
   ```

   Replace `<file_path>` with the PNG file path the user provided.

5. **On success:** Show the output file paths and file sizes to the user. Mention:
   - SVG 檔可直接在瀏覽器或任何向量編輯器中開啟
   - AI 檔可在 Adobe Illustrator 中開啟編輯
   - 如果效果不滿意，可以調整 `--detail` 或 `--colormode binary`（適合黑白圖案）

6. **On failure:** Show the error message. Common issues:
   - File not found → 確認檔案路徑
   - Unsupported format → 目前支援 PNG, JPG, BMP, GIF
   - Missing dependencies → 執行 `uv sync`
