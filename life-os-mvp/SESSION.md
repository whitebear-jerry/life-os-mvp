# ⚡ Codex Session 協定
**每次開始必讀，每次結束必更新。**

## 🚀 下次開場白（複製這段給新 session 的 Codex）
請讀取 SESSION.md，繼續上次工作。
上次中斷在：Codex 已完成 EP1 V3.3 螢幕錄影 MVP pipeline 驗證，並將 `tools/video-pipeline/screen-record-to-youtube.py` 的 Whisper 預設模型升級為 `large-v3`。已另產出 GDrive 測試字幕 `04-subtitles-large-v3-test.srt`，但測試結果顯示 large-v3 在本素材上只命中指定關鍵詞 2/5，且有簡體、英文幻覺與片段錯亂；現存 `04-subtitles-screen-MVP.srt` 反而命中 5/5。
下一步應該做：先 `git fetch origin && git switch codex/life-os-mvp && git pull origin codex/life-os-mvp`，再讀 Obsidian `AI-Checkpoint.md`、`CLAUDE/工作日誌.md`、`我的思維框架/Life OS 營銷總控台.md`；請使用者或 Claude 決定是否真的採用 large-v3。若要發布，目前建議以 `04-subtitles-screen-MVP.srt` 為底人工修，而不是直接採用 `04-subtitles-large-v3-test.srt`。

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
