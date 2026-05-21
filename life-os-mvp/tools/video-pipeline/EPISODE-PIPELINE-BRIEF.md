# Codex Brief — EP 影片自動化 pipeline（episode-pipeline.py）

> 給 Codex：請依本 Brief 在 `tools/video-pipeline/` 新建 `episode-pipeline.py`，把 EP1 已人工驗證的三項突破固化成可重複跑的腳本，供 EP2-12 直接使用。完成後用 EP1 素材回歸驗證，再更新 SESSION.md。

---

## 0. 背景（為什麼要做）

EP1（大腦 RAM 清倉術）的最終成品是「手動跑出來的」，沒有寫進腳本。現存的
`screen-record-to-youtube.py` 是**舊版 V3.3**，做法已被淘汰：

- ❌ 它**燒死字幕**（hardsub）→ 我們最後決定改用 YouTube CC 分離字幕軌
- ❌ 它用**字元數硬切**重組字幕（`split_long_word` 會把詞切斷）→ 造成「幾個｜APP」斷字感
- ❌ 它**不剪靜音停頓** → 影片拖沓

`episode-pipeline.py` 要把下面三項 EP1 已驗證的做法變成預設流程。**不要**沿用舊的燒字幕／字元硬切邏輯，但可以重用它的工具函式（`srt_time`、`load_vocab`、`apply_vocab`、`transcribe` 的 device 選擇等）。

---

## 1. 三項已驗證突破（必須全部實作）

### 突破 A：自動剪靜音停頓（auto-editor）
- 工具：`auto-editor`，裝在 `~/.venv-autoeditor`（PEP668 externally-managed，用 venv）。
- 參數：`--margin 0.4sec`（EP1 實測：剪掉約 10.6% 時長，7:50 → 7:01，節奏「剛好」）。
- 產物：剪好的影片（clean，無字幕）。

### 突破 B：字幕＝word_timestamps + 語意分段「合併」（絕不切斷）
- **關鍵：對「剪過的影片」重新轉錄**，不要用原始未剪檔（剪掉停頓後時間軸已改變，用舊時間軸會 desync）。
- Whisper `word_timestamps=True`。
- 每個 Whisper segment 的真實時間 = `words[0].start` / `words[-1].end`（不要信 segment 自己的 start/end，那是假的 2 秒桶）。
- 合併**相鄰的完整 segment** 到目標 12-15 字（TARGET=12、MAX≈16）。
- **永遠不要切斷一個 segment**（切斷就是上一版「斷字」的根因；停頓被剪掉後語音變連續，沒有空隙可切，所以只能用 Whisper 自己的語意分段邊界來合併）。
- 套用 `vocab.json` 修正錯字。清理時間重疊。
- EP1 結果：120 段。

### 突破 C：乾淨影片 + 獨立 SRT（不燒字幕）
- 最終輸出 = 乾淨 MP4（無字幕）+ 一份獨立 `.srt`，供上傳 YouTube 成中文 CC。
- **不要** burn-in。（如未來要做 Shorts 直式版再另開 `--burn` 旗標，本期不做。）

---

## 2. 模型決策（重要）

- **預設 `--model medium`**。
- EP1 實測：`medium` 指定關鍵詞命中 5/5；`large-v3` 只 2/5，且有簡體字、英文幻覺、片段錯亂。
- 保留 `--model` 可覆寫，但預設值改回 `medium`（不要用 large-v3 當預設）。

---

## 3. CLI 設計

```bash
python episode-pipeline.py <input.mov> \
  --out-dir "<該集 GDrive 資料夾>" \
  --ep 01 \
  --model medium \
  --margin 0.4 \
  [--skip-cut]          # 已有剪好的影片，只跑字幕
  [--skip-transcribe]   # 已有 SRT，只重燒/重輸出
  [--transcribe-only]   # 只產 SRT + transcript，不輸出影片
```

### 階段流程
1. **剪靜音**（auto-editor，margin 0.4）→ 中間檔 cut 影片
2. **正規化**：若非 1920×1080 / 標準 fps，用 ffmpeg scale + fps（可用 `h264_videotoolbox` 硬體編碼加速）
3. **轉錄剪過的影片**（Whisper word_timestamps，預設 medium）
4. **建字幕段**（語意合併、絕不切斷）+ 套 vocab
5. **寫 SRT + transcript**
6. 最終乾淨影片 = 第 1-2 步產物（不燒字幕）

---

## 4. 輸入 / 輸出命名規約

每集資料夾位於 GDrive：
`.../我的雲端硬碟/Life OS/marketing/season1-降噪人生/episode-NN-<主題>/`

| 角色 | 檔名 |
|------|------|
| 輸入 | `03-screen-recording-MVP.mov` |
| 輸出・乾淨影片 | `05-final-video-autocut.mp4` |
| 輸出・字幕 | `EP{NN}-字幕-zh-TW-autocut.srt` |
| 輸出・逐字稿 | `transcript-autocut.txt` |

---

## 5. 三倉鐵則（務必遵守）

- **內容檔（mp4/srt/txt）只寫到 GDrive 的該集資料夾，不要寫進 repo。**
- **只有程式碼（`episode-pipeline.py`）進 repo。**
- `vocab.json` 已存在於 `tools/video-pipeline/vocab.json`，pipeline 讀它；發現新錯字就往裡加。
- 環境：python3.11/3.12 + venv；auto-editor 在 `~/.venv-autoeditor`；ffmpeg-full 在 `/opt/homebrew/Cellar/ffmpeg-full/*/bin/ffmpeg`。
- **不要**再跑已淘汰的 `auto-edit-video.py`、`shorts-cutter.py`。

---

## 6. 驗收 Gate（用 EP1 回歸測試）

對 EP1 原始檔重跑：
`.../marketing/season1-降噪人生/episode-01-大腦RAM清倉術/03-screen-recording-MVP.mov`

通過條件：
- ✅ 輸出影片時長 ≈ 7:01（±5 秒），與既有 `05-final-video-autocut.mp4` 相符
- ✅ SRT 段數 ≈ 120（±10），無時間重疊
- ✅ 關鍵詞拼寫正確且存在：`蔡加尼克`、`Readmoo`、`房貸`、`瑣事`、`第二大腦`、`Pubu`、`Notion`、`Obsidian`
- ✅ 無整段斷字（不可出現把一個詞拆兩行的情形）
- ✅ 最終影片無燒入字幕（乾淨畫面）

跑完把 EP1 既有成品當對照，不要覆蓋掉現有的 `05-final-video-autocut.mp4` / `EP01-字幕-zh-TW-autocut.srt`（輸出到暫存名或加 `-regen` 後綴比對，確認 OK 再決定是否取代）。

---

## 7. 完成後

1. 更新 `SESSION.md`：記錄 `episode-pipeline.py` 已建立 + EP1 回歸結果。
2. 在 `AI-Checkpoint.md`（Obsidian）寫一句交接：pipeline 可用，EP2 可直接 `python episode-pipeline.py 03-screen-recording-MVP.mov --out-dir <ep02 folder> --ep 02`。
3. push（只 push 程式碼：`episode-pipeline.py`、必要的 `vocab.json` 更新）。
