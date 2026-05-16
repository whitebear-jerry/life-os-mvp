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
上次中斷在：IG-CARDS-DESIGN 探索完成，已建立 4 個 1080×1350 HTML 字卡背景方向；Fix-1/Fix-2 已完成並推送；EP1 仍等待錄音。
下一步應該做：先執行 `git fetch origin`、`git pull origin codex/life-os-mvp`，確認 GDrive 已掛載（`ls "GDrive/Life OS/"` 應看到 audio、deliverables、marketing、scripts、templates、tracking）；請用戶從 `marketing/ig-cards/design-explore/` 的 A/B/C/D 四個方向中選定 IG 字卡視覺方向。若要繼續 EP1 pipeline，確認錄音檔 `GDrive/Life OS/marketing/season1-降噪人生/episode-01-大腦RAM清倉術/03-raw-audio.m4a` 是否已放入；若已放入，安裝影音依賴並將字幕、影片、Shorts、金句圖卡全部輸出到 GDrive 路徑。

## 最近一次 session
- 電腦：baizheweideMacBook-Air.local
- 日期：2026-05-16
- 分支：codex/life-os-mvp
- 完成：
  1. IG-CARDS-DESIGN：建立 4 個 IG 字卡背景探索 HTML，路徑 `marketing/ig-cards/design-explore/`
  2. 四方向：A Notion 點陣工具感、B 白熊品牌浮水印、C 柔光漸層幾何弧形、D 《降噪人生》水波/書本微飾
  3. 使用 Chrome headless 輸出 4 張 1080×1350 截圖到 `/private/tmp/ig-card-A.png` 至 `/private/tmp/ig-card-D.png` 做視覺確認
  4. Fix-1/Fix-2 已完成（9 個 HTML Kobo URL tracking 清除、footer 簡化），commit `5c1f874` 已 push，`gh-pages` deploy `f671771` 已 push
  5. **Google Drive 內容遷移**：136 個檔案搬到 GDrive `Life OS/`，建立完整 marketing/deliverables/templates/tracking 結構
- 下次從：請用戶選定 IG 字卡方向 A/B/C/D，再進入批次生產；EP1 則仍等待用戶放入錄音 `03-raw-audio.m4a`（路徑改為 GDrive），再跑 pipeline。

## 未完成但已 push 的 WIP
- `f9ec761`：V2 EP1「大腦 RAM 清倉術」簡報素材已補齊；尚未錄音、轉字幕、合成影片與剪 Shorts。

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
