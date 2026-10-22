# 白熊 YouTube 第一季影片 Pipeline SOP

本資料夾管理第一季《降噪人生》12 集影片素材。影片格式是「簡報 + 旁白」，不露臉；長片上 YouTube，短片拆成 IG Reels / YouTube Shorts / Threads 素材。

## 重要路徑

- 本季資料夾：`marketing/season1-降噪人生/`
- Pipeline 腳本：`tools/video-pipeline/`
- 圖卡模板：`marketing/quote-card-template.html`
- 原 Brief 提到 `scripts/video-pipeline/`，但 repo 內 `scripts/` 是 Google Drive 私密 symlink 並被 `.gitignore` 保護；因此公開 pipeline 腳本放在 `tools/video-pipeline/`。

## 每集標準檔案

- `00-notebooklm-extract.md`：NotebookLM 查詢素材
- `01-slides.pdf`：NotebookLM 生成或人工匯出的簡報
- `02-script.md`：Claude 講稿
- `03-raw-audio.m4a`：用戶錄音，忽略 Git，放 Google Drive
- `04-subtitles.srt`：Whisper 輸出字幕
- `05-final-video.mp4`：剪輯成品，忽略 Git，放 Google Drive
- `06-shorts/`：3 支短片，忽略 Git
- `07-quote-cards/`：3 張金句圖卡
- `08-meta-post.md`：跨平台貼文文案

## 環境安裝

建議使用 Python 3.11+。

```bash
cd /Users/baizhewei/Documents/New\ project/life-os-mvp
python3 -m venv .venv-video
source .venv-video/bin/activate
pip install -r tools/video-pipeline/requirements.txt
playwright install chromium
```

系統依賴：

```bash
brew install ffmpeg poppler
```

注意：

- `openai-whisper` 需要 `ffmpeg`。
- `pdf2image` 需要 `poppler`。
- `quote-card-generator.py` 需要 `playwright install chromium`。
- `moviepy` 燒字幕可能受本機字型與 ImageMagick/新版 MoviePy 行為影響；若失敗，先輸出無字幕影片，再用剪映或 CapCut 匯入 `04-subtitles.srt`。

## 每集開工流程

以下以 EP1 為例：

```bash
EP="marketing/season1-降噪人生/episode-01-大腦RAM清倉術"
PIPE="tools/video-pipeline"
```

1. 準備素材

```bash
# 由 V2 或 NotebookLM 產出
# $EP/00-notebooklm-extract.md
# $EP/01-slides.pdf
# $EP/02-script.md

# 用戶錄音後放入
# $EP/03-raw-audio.m4a
```

2. 轉錄字幕

```bash
python "$PIPE/whisper-transcribe.py" "$EP/03-raw-audio.m4a" --model medium --language zh --output-dir "$EP"
mv "$EP/subtitles.srt" "$EP/04-subtitles.srt"
```

3. 簡報 + 旁白合成長片

```bash
python "$PIPE/slide-to-video.py" \
  --pdf "$EP/01-slides.pdf" \
  --audio "$EP/03-raw-audio.m4a" \
  --script "$EP/02-script.md" \
  --srt "$EP/04-subtitles.srt" \
  --output "$EP/05-slide-video.mp4"
```

4. 自動剪輯與字幕燒入

```bash
python "$PIPE/auto-edit-video.py" \
  "$EP/05-slide-video.mp4" \
  --srt "$EP/04-subtitles.srt" \
  --output "$EP/05-final-video.mp4"
```

5. 產出 3 支短片

```bash
python "$PIPE/shorts-cutter.py" \
  --video "$EP/05-final-video.mp4" \
  --script "$EP/02-script.md" \
  --output-dir "$EP/06-shorts"
```

6. 產出 3 張金句圖卡

```bash
python "$PIPE/quote-card-generator.py" \
  --script "$EP/02-script.md" \
  --output-dir "$EP/07-quote-cards" \
  --template marketing/quote-card-template.html
```

## 收工檢查

```bash
git status --short --untracked-files=all
git diff --stat
```

確認不要進 Git：

- `03-raw-audio.m4a`
- `05-final-video.mp4`
- `06-shorts/`
- 任何大型 `.mp4` / `.m4a`

可以進 Git：

- `00-notebooklm-extract.md`
- `02-script.md`
- `04-subtitles.srt`（若需要版本化）
- `07-quote-cards/*.png`（若要公開使用）
- `08-meta-post.md`

## 常見錯誤

### `ffmpeg not found`

安裝：

```bash
brew install ffmpeg
```

### `Unable to get page count` 或 PDF 無法轉圖

通常是缺 Poppler：

```bash
brew install poppler
```

### Playwright 找不到 Chromium

```bash
playwright install chromium
```

### 字幕燒入失敗

先確認 `04-subtitles.srt` 正常。若 `moviepy` 的 `TextClip` 在本機失敗，先輸出無字幕影片，再把 `04-subtitles.srt` 匯入 CapCut / 剪映 / YouTube Studio。

### 自動刪贅字不準

目前 `auto-edit-video.py` 的贅字清單在 `tools/video-pipeline/config.json`。中文贅字精準剪除需要更細的逐字時間戳；第一版以靜音剪除為主，贅字清單保留為後續逐字剪輯升級點。

## V1 本機驗證紀錄（2026-05-15）

已通過：

- 12 個 episode 資料夾建立完成。
- 每集都具備 `00-notebooklm-extract.md`、`01-slides.pdf`、`02-script.md`、`04-subtitles.srt`、`07-quote-cards/`、`08-meta-post.md`。
- `03-raw-audio.m4a`、`05-final-video.mp4`、`06-shorts/` 已被 `.gitignore` 正確排除。
- 5 支 Python 腳本 `--help` 可正常執行。
- `PYTHONPYCACHEPREFIX=/private/tmp/codex-pycache python3 -m py_compile tools/video-pipeline/*.py` 通過。

未在本機跑完整影音流程，原因：

- 目前 Python 環境尚未安裝 `moviepy`、`openai-whisper`、`playwright` 等套件。
- `pdftoppm` 尚未出現在 PATH，代表 Poppler 可能尚未安裝或 PATH 未設定。
- `quote-card-generator.py` 測試時回報缺 `playwright`，需先執行安裝步驟。

安裝完本檔「環境安裝」區塊後，再用 EP1 或任一 1-2 分鐘測試音檔跑完整 SOP。

## 每個腳本的輸入輸出

| 腳本 | 輸入 | 輸出 |
|------|------|------|
| `whisper-transcribe.py` | `03-raw-audio.m4a` | `subtitles.srt`、`transcript.txt` |
| `slide-to-video.py` | `01-slides.pdf`、`03-raw-audio.m4a`、`02-script.md`、`04-subtitles.srt` | `05-slide-video.mp4` |
| `auto-edit-video.py` | `05-slide-video.mp4`、`04-subtitles.srt` | `05-final-video.mp4` |
| `shorts-cutter.py` | `05-final-video.mp4`、`02-script.md` | `06-shorts/short-01.mp4` 等 |
| `quote-card-generator.py` | `02-script.md`、`marketing/quote-card-template.html` | `07-quote-cards/quote-card-01.png` 等 |

## 第一季 12 集

1. EP1：大腦 RAM 清倉術
2. EP2：心靈防火牆
3. EP3：第二大腦 Notion 外接硬碟
4. EP4：攝影機思維除錯
5. EP5：微習慣自動導航
6. EP6：反脆弱躺平術
7. EP7：不做清單
8. EP8：戰略性暫停
9. EP9：三層人際同心圓
10. EP10：願景視覺化
11. EP11：宇宙觀光客
12. EP12：Life OS 系統宣言
