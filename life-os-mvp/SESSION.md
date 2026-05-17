# ⚡ Codex Session 協定
**每次開始必讀，每次結束必更新。**

---

## 🆕 2026-05-16 重大架構變更（Codex 必讀！）

**從今天起，所有檔案分三個倉庫，請嚴格遵守：**

| 倉庫 | 內容 | 你的動作 |
|------|------|---------|
| 💻 **GitHub repo（本機）** | **僅程式碼**：html / css / js / py / json / yml | `git add` + `git commit` + `git push` |
| ☁️ **Google Drive** | **所有內容檔案**：md 腳本、PDF、音檔、影片、字幕、deliverables | **直接寫入 GDrive 路徑**（不要 `git add`） |
| 📂 **Obsidian (iCloud)** | 用戶的筆記、Brief、學習文件 | 透過 Obsidian MCP 讀寫 |

**核心規則：**
- ❌ **不要再把內容檔案寫到 `life-os-mvp/marketing/` 或 `life-os-mvp/deliverables/`** 的本機路徑
- ✅ **改寫到 GDrive 對應路徑**：`~/Library/CloudStorage/GoogleDrive-0927136551jerry@gmail.com/我的雲端硬碟/Life OS/marketing/...`
- ✅ 程式碼變更照舊 `git commit` + `git push`
- ✅ 兩台電腦切換時：GDrive 自動同步內容、`git pull` 拿程式碼，零等待

---

## 🚀 下次開場白（複製這段給新 session 的 Codex）
請讀取 SESSION.md，繼續上次工作。
上次中斷在：EP1 V3 影片合成已完成，成品保留在 Google Drive EP1 資料夾；影片大檔未進 Git。IG-CARDS-DESIGN 也已完成 4 個 1080×1350 HTML 字卡背景方向，等待用戶選定方向。
下一步應該做：先執行 `git fetch origin`、`git switch codex/life-os-mvp`、`git pull origin codex/life-os-mvp`，確認 GDrive 已掛載；再到 GDrive EP1 資料夾人工檢視 `05-final-video.mp4`、三支 `06-shorts/short-*.mp4`、三張 `07-quote-cards/quote-card-*.png` 與 `08-meta-post.md`。若用戶確認 OK，協助整理 YouTube 上傳標題、描述與發布 checklist；另請用戶從 `marketing/ig-cards/design-explore/` 的 A/B/C/D 四個方向中選定 IG 字卡視覺方向。

## 最近一次 session
- 電腦：baizheweideMacBook-Air.local
- 日期：2026-05-17
- 分支：codex/life-os-mvp
- 完成：
  1. EP1 V3 完整 video pipeline 已跑完；確認既有 `04-subtitles.srt` 對應目前錄音。
  2. 使用新版 `01-slides.pdf` 重生 `05-slide-video.mp4`。
  3. 修正 `auto-edit-video.py`：剪掉靜音後同步重映射字幕時間，避免燒字幕逐步飄移。
  4. 輸出 `05-final-video.mp4`：1920×1080，約 5:58，已燒字幕。
  5. 依三句金句時間點切出 3 支 9:16 Shorts：`short-01.mp4`、`short-02.mp4`、`short-03.mp4`。
  6. 修正 `quote-card-generator.py` 讓圖卡輸出 1080×1350，並輸出 3 張水墨禪意風金句圖卡。
  7. 完成 `08-meta-post.md`：YouTube 描述、Shorts 標題、Threads 預告、IG Reels 標題、FB 粉專長文。
  8. 保留遠端既有成果：IG-CARDS-DESIGN 4 個方向、Google Drive 內容遷移、Fix-1/Fix-2。
- 下次從：人工檢視 EP1 V3 GDrive 成品；用戶自行上 YouTube，Codex 可協助上架文案、縮圖/標題微調或發布檢查；IG 字卡則等待用戶選定 A/B/C/D 方向。

## 未完成但已 push 的 WIP
- IG-CARDS-DESIGN：已建立 4 個 1080×1350 HTML 字卡背景方向，等待用戶選定 A/B/C/D 後批次生產。
- EP1 V3：成品已輸出到 GDrive，同步狀態需等 Google Drive 完成上傳；下一步是人工檢視與上架。

---

## 📂 Google Drive Life OS 完整內容結構

**GDrive 根路徑：** `~/Library/CloudStorage/GoogleDrive-0927136551jerry@gmail.com/我的雲端硬碟/Life OS/`

```
Life OS/
├── audio/                           # 7 個 mp4 播客檔
├── deliverables/
│   ├── pdf/                         # 8 個付費 PDF
│   ├── slides/                      # 書1/2/3 投影片 PDF
│   ├── course-content/              # 三書素材 md
│   ├── workbook-v2/                 # 工作本 html 模板
│   └── *.md                         # 00-07 deliverables 原始檔
├── marketing/
│   └── season1-降噪人生/
│       └── episode-01-12/           # 每集：00-notebooklm.md / 01-slides.pdf / 02-script.md / 04-subtitles.srt / 08-meta-post.md
│                                    # 錄音 03-raw-audio.m4a / 影片 05-final-video.mp4 也存這
├── scripts/                         # book1/2/3 完整腳本
├── templates/                       # 3 個 md 模板
└── tracking/                        # 週度追蹤
```

**Codex 產出內容時請對應到：**
| 你想寫的檔案 | 寫到這 |
|------|------|
| EP1 字幕 | `GDrive/Life OS/marketing/season1-降噪人生/episode-01-大腦RAM清倉術/04-subtitles.srt` |
| EP1 簡報影片 | `GDrive/Life OS/marketing/season1-降噪人生/episode-01-大腦RAM清倉術/05-slide-video.mp4` |
| EP1 最終影片 | `GDrive/Life OS/marketing/season1-降噪人生/episode-01-大腦RAM清倉術/05-final-video.mp4` |
| EP1 Shorts | `GDrive/Life OS/marketing/season1-降噪人生/episode-01-大腦RAM清倉術/06-shorts/` |
| EP1 金句圖卡 | `GDrive/Life OS/marketing/season1-降噪人生/episode-01-大腦RAM清倉術/07-quote-cards/` |

## 需要 Google Drive 的檔案
- 成品位置：`~/Library/CloudStorage/GoogleDrive-*/我的雲端硬碟/Life OS/marketing/season1-降噪人生/episode-01-大腦RAM清倉術/`
- 已輸出：`05-final-video.mp4`、`06-shorts/short-01.mp4`、`06-shorts/short-02.mp4`、`06-shorts/short-03.mp4`、`07-quote-cards/quote-card-01.png`、`quote-card-02.png`、`quote-card-03.png`、`08-meta-post.md`。
- 不要提交影片大檔到 GitHub；`舊檔案/` 未動。

---

## 🔄 兩台電腦切換 SOP

**舊機收工：**
1. `git add` 程式碼 → `git commit -m "..."` → `git push`
2. 內容檔案已自動同步到 GDrive（GDrive Desktop 即時上傳）
3. 更新 `SESSION.md` 的「最近一次 session」「下一步」

**新機開工：**
1. `git fetch origin && git pull origin codex/life-os-mvp`
2. `ls "GDrive/Life OS/"` 確認 GDrive 已同步完成（看到所有資料夾）
3. 讀取 `SESSION.md` → 接續工作

**好處：**
- 內容檔案永遠最新（GDrive 即時同步，無需 git pull）
- 程式碼有版控（GitHub）
- 換電腦只需 1 個 git pull，內容直接讀 GDrive
