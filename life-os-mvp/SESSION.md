# ⚡ Codex Session 協定
**每次開始必讀，每次結束必更新。**

## 🚀 下次開場白（複製這段給新 session 的 Codex）
請讀取 SESSION.md，繼續上次工作。
**本次任務：建立 EP 影片自動化 pipeline。** 完整規格在 `tools/video-pipeline/EPISODE-PIPELINE-BRIEF.md`，請先讀它，照規格在 `tools/video-pipeline/` 新建 `episode-pipeline.py`。
重點：把 EP1 已人工驗證的三項突破固化成腳本 —— (A) auto-editor 剪靜音 margin 0.4；(B) Whisper word_timestamps + 語意分段「合併、絕不切斷」，預設模型改回 `medium`（large-v3 在本素材命中率較差）；(C) 輸出乾淨影片 + 獨立 SRT，不燒字幕。現存 `screen-record-to-youtube.py` 是淘汰的舊版（燒字幕＋字元硬切），可重用工具函式但不要沿用其字幕邏輯。
下一步應該做：先 `git fetch origin && git switch codex/life-os-mvp && git pull origin codex/life-os-mvp`，讀 `EPISODE-PIPELINE-BRIEF.md` 與 Obsidian `AI-Checkpoint.md`、`CLAUDE/工作日誌.md`；建好 `episode-pipeline.py` 後用 EP1 原始檔 `episode-01-大腦RAM清倉術/03-screen-recording-MVP.mov` 跑驗收 Gate（時長≈7:01、SRT≈120 段、關鍵詞拼寫正確、無斷字、無燒字幕），通過再 push。

## 最近一次 session
- 電腦：baizheweideMacBook-Air.local
- 日期：2026-05-20
- 分支：codex/life-os-mvp
- 完成：`screen-record-to-youtube.py` 預設 Whisper model 已是 `large-v3`；已用 EP1 螢幕錄影只重跑 Whisper 測試，輸出 `04-subtitles-large-v3-test.srt`，未覆蓋正式影片或正式字幕。
- 下次從：檢查 `04-subtitles-large-v3-test.srt` 是否值得採用；目前測試結論是 large-v3 關鍵詞命中率 2/5，現存 medium 版 `04-subtitles-screen-MVP.srt` 命中率 5/5。

## 未完成但已 push 的 WIP
- EP1 V3.1 pipeline 修正已 push：`auto-edit-video.py`、`shorts-cutter.py`、`quote-card-generator.py`、`config.json`、`quote-card-template.html`。
- IG-CARDS-DESIGN 已 push 4 個探索方向，等待使用者選 A/B/C/D。
- Claude 工作日誌已標註 V3.3 螢幕錄影模式為後續方向，需等使用者提供 `03-screen-recording-MVP.mov` 或完整螢幕錄影。

## 需要 Google Drive 的檔案
- 已在 GDrive 輸出 EP1 V3.3 MVP 成品：`05-final-video-MVP.mp4`、`04-subtitles-screen-MVP.srt`、`04-subtitles-screen-MVP.ass`、`transcript-screen-MVP.txt`。
- large-v3 測試字幕：`04-subtitles-large-v3-test.srt`，只供比對，不是正式成品。
- 沒有需要手動搬到 GDrive 的新檔案。
- 下一步若修字幕，直接修改 GDrive EP1 的 `04-subtitles-screen-MVP.srt`，再跑 `screen-record-to-youtube.py --skip-transcribe` 重新燒錄，不要跑廢棄的 `auto-edit-video.py`、`shorts-cutter.py`。
