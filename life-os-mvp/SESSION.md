# ⚡ Codex Session 協定
**每次開始必讀，每次結束必更新。**

## 🔄 Git 同步協定（標準・2026-05-21 起）
使用者**不手動跑 git**。AI（Claude / Codex）全程代勞：
- **開工**：自動 `git fetch && git switch codex/life-os-mvp && git pull`（抓最新）。
- **收工**：自動 `git add <相關檔> && git commit && git push`（上傳，讓另一台電腦與雲端同步）。
- 使用者只講中文，不需被問「要不要 push」。內容檔（mp4/srt/pdf）走 GDrive 自動同步、筆記走 iCloud 自動同步；**只有程式碼**走這條 git 流程。

## 🚀 下次開場白（複製這段給新 session 的 Codex）
請讀取 SESSION.md，繼續上次工作。
**本次任務：EP 影片自動化 pipeline 已建立並通過 EP1 回歸。**
下一步可直接用 `tools/video-pipeline/episode-pipeline.py` 跑 EP2-12。EP2 範例：
`python tools/video-pipeline/episode-pipeline.py "<EP2 資料夾>/03-screen-recording-MVP.mov" --out-dir "<EP2 資料夾>" --ep 02 --model medium --margin 0.4`
重點：pipeline 會 auto-editor 剪靜音（margin 0.4）、正規化成 1920x1080/30fps、對剪後影片用 Whisper `medium` + `word_timestamps` 轉錄、用完整 Whisper segment 合併字幕（不切字）、輸出乾淨 MP4 + 獨立 SRT/TXT，不燒字幕。中間檔預設放本機 temp，避免 GDrive I/O 拖慢。

## 最近一次 session
- 電腦：baizheweideMac-mini.local
- 日期：2026-05-21
- 分支：codex/life-os-mvp
- 完成：新增 `tools/video-pipeline/episode-pipeline.py`；`vocab.json` 增加 `REIT DOMO` / `REITDOMO` → `Readmoo`。
- EP1 回歸：用 `03-screen-recording-MVP.mov` 跑出 `05-final-video-autocut-regen.mp4`、`EP01-字幕-zh-TW-autocut-regen.srt`、`transcript-autocut-regen.txt`。驗收通過：影片 422.058s（約 7:02）、1920x1080/30fps、SRT 120 段、0 重疊、0 多行/超長段、關鍵詞 8/8 命中（蔡加尼克、Readmoo、房貸、瑣事、第二大腦、Pubu、Notion、Obsidian），影片只有 video/audio stream，未燒字幕。
- 收工 SOP：已定位並更新 Obsidian `AI-Checkpoint.md` 與 `CLAUDE/工作日誌.md`；`link.html` 有安全的樣式調整，需隨本次收工 commit/push，並同步部署 `gh-pages`。
- 下次從：用 `episode-pipeline.py` 處理 EP2；若 EP2 原始檔已在 GDrive 該集資料夾，直接跑上方命令即可。

## 未完成但已 push 的 WIP
- EP1 V3.1 pipeline 修正已 push：`auto-edit-video.py`、`shorts-cutter.py`、`quote-card-generator.py`、`config.json`、`quote-card-template.html`。
- IG-CARDS-DESIGN 已 push 4 個探索方向，等待使用者選 A/B/C/D。
- Claude 工作日誌已標註 V3.3 螢幕錄影模式為後續方向，需等使用者提供 `03-screen-recording-MVP.mov` 或完整螢幕錄影。

## 需要 Google Drive 的檔案
- EP1 回歸輸出在 GDrive episode-01 資料夾：`05-final-video-autocut-regen.mp4`、`EP01-字幕-zh-TW-autocut-regen.srt`、`transcript-autocut-regen.txt`。
- 舊版 `screen-record-to-youtube.py`、`auto-edit-video.py`、`shorts-cutter.py` 不再作為 EP 主流程；保留作歷史工具參考。
- 下一步若要正式替換 EP1 autocut 成品，先人工快速看過 `*-regen` 檔，再決定是否覆蓋無 `-regen` 的正式檔名。
