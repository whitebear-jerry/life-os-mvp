# ⚡ Codex Session 協定
**每次開始必讀，每次結束必更新。**

## 🚀 下次開場白（複製這段給新 session 的 Codex）
請讀取 SESSION.md，繼續上次工作。
上次中斷在：Codex 已完成 EP1 V3.3 螢幕錄影 MVP pipeline 驗證，新增 `tools/video-pipeline/screen-record-to-youtube.py`，並輸出 GDrive EP1 `05-final-video-MVP.mp4`、`04-subtitles-screen-MVP.srt`、`04-subtitles-screen-MVP.ass`、`transcript-screen-MVP.txt`。本版只做 Whisper 字幕與 ffmpeg 燒字幕，沒有 auto-edit、沒有 Shorts、沒有圖卡。
下一步應該做：先 `git fetch origin && git switch codex/life-os-mvp && git pull origin codex/life-os-mvp`，再讀 Obsidian `AI-Checkpoint.md`、`CLAUDE/工作日誌.md`、`我的思維框架/Life OS 營銷總控台.md`；請使用者人工審片 `05-final-video-MVP.mp4`，重點檢查字幕錯字與是否接受字幕壓到投影片下緣。若要發布，建議先人工修正 `04-subtitles-screen-MVP.srt` 中專有名詞，再用 `screen-record-to-youtube.py --skip-transcribe` 重燒影片。

## 最近一次 session
- 電腦：baizheweideMacBook-Air.local
- 日期：2026-05-20
- 分支：codex/life-os-mvp
- 完成：EP1 V3.3 螢幕錄影 MVP pipeline 驗證；新增 `screen-record-to-youtube.py`，使用 Whisper medium + zh 與 ffmpeg-full/libass 燒中文字幕，輸出 `05-final-video-MVP.mp4` 到 GDrive。
- 下次從：請使用者審片 `05-final-video-MVP.mp4`；若 OK，修正 SRT 專有名詞後重燒；若不 OK，先調整字幕位置/大小/樣式再重燒。

## 未完成但已 push 的 WIP
- EP1 V3.1 pipeline 修正已 push：`auto-edit-video.py`、`shorts-cutter.py`、`quote-card-generator.py`、`config.json`、`quote-card-template.html`。
- IG-CARDS-DESIGN 已 push 4 個探索方向，等待使用者選 A/B/C/D。
- Claude 工作日誌已標註 V3.3 螢幕錄影模式為後續方向，需等使用者提供 `03-screen-recording-MVP.mov` 或完整螢幕錄影。

## 需要 Google Drive 的檔案
- 已在 GDrive 輸出 EP1 V3.3 MVP 成品：`05-final-video-MVP.mp4`、`04-subtitles-screen-MVP.srt`、`04-subtitles-screen-MVP.ass`、`transcript-screen-MVP.txt`。
- 沒有需要手動搬到 GDrive 的新檔案。
- 下一步若修字幕，直接修改 GDrive EP1 的 `04-subtitles-screen-MVP.srt`，再跑 `screen-record-to-youtube.py --skip-transcribe` 重新燒錄，不要跑廢棄的 `auto-edit-video.py`、`shorts-cutter.py`。
