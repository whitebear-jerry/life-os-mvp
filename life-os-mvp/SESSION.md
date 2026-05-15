# ⚡ Codex Session 協定
**每次開始必讀，每次結束必更新。**

## 🚀 下次開場白（複製這段給新 session 的 Codex）
請讀取 SESSION.md，繼續上次工作。
上次中斷在：V2 EP1「大腦 RAM 清倉術」素材已完成並 push，尚未錄音與跑完整影音 pipeline。
下一步應該做：先確認 EP1 錄音檔 `marketing/season1-降噪人生/episode-01-大腦RAM清倉術/03-raw-audio.m4a` 是否已放入；若已放入，安裝 `tools/video-pipeline/requirements.txt`、`playwright install chromium`、`brew install poppler`，再依 SOP 產生 `04-subtitles.srt`、`05-slide-video.mp4`、`05-final-video.mp4`、`06-shorts/` 與 `07-quote-cards/`。

## 最近一次 session
- 電腦：baizheweideMac-mini.local
- 日期：2026-05-16
- 分支：codex/life-os-mvp
- 完成：V2 EP1 NotebookLM 素材、完整講稿與 10 頁 `01-slides.pdf` 已補齊，PDFKit 確認 10 頁並抽查渲染正常，commit `f9ec761` 已 push。
- 下次從：等待用戶放入 EP1 錄音 `03-raw-audio.m4a`，再跑 Whisper 字幕與簡報合成影片流程。

## 未完成但已 push 的 WIP
- `f9ec761`：V2 EP1「大腦 RAM 清倉術」簡報素材已補齊；尚未錄音、轉字幕、合成影片與剪 Shorts。

## 需要 Google Drive 的檔案
無。這次產出的 `01-slides.pdf` 已存於 repo 的 EP1 資料夾；後續錄音、成片與 Shorts 仍應放 Google Drive，不進 GitHub。
