# ⚡ Codex Session 協定
**每次開始必讀，每次結束必更新。**

## 最近一次 session
- 電腦：baizheweideMac-mini.local
- 日期：2026-05-15
- 分支：codex/life-os-mvp
- 完成：U2 精簡 link-in-bio 頁已建立，給 IG / Threads 個人檔案連結使用。
  - 新增 `link.html`：白熊頭像、品牌一句話、三書介紹、三平台購買按鈕、IG / YouTube 文字收尾
  - 三書購買連結依 `主題學習/創作/三書購買連結.md` 官方索引填入
  - 未修改 `index.html` / `offer.html` / `starter.html` 等既有頁面
  - 待部署到 `gh-pages` 後線上 URL：`https://whitebear-jerry.github.io/life-os-mvp/link.html`
- 前次完成：U1（三書 × 三通路 9 個 CTA 全站更新）已完成並通過 Claude 督導審查。
  - 功能 commit `6e5c78d` → `codex/life-os-mvp`
  - 部署 commit `aa261c6` → `gh-pages`
  - Fix-Sync commit `2901768` / `d6a74dc`（deliverables 源稿 + .gitignore）
- 本 session Claude 端另外完成的「戰略 + 整理」工作（都在 Obsidian，靠 iCloud 同步）：
  - 建立 `我的思維框架/白熊資產地圖 v1.md`（新的戰略總指南，取代散落的舊策略檔）
  - `我的思維框架/Life OS 營銷總控台.md` 重寫為 v3（任務看板，戰略指向資產地圖）
  - 9 份過時策略檔移入 `我的思維框架/_Archive/`（含 README 索引）
  - 建立 `主題學習/創作/三書購買連結.md`（三書 × 三通路官方 URL 唯一索引）
  - 建立 `我的思維框架/白熊品牌帳號設定 SOP.md`（IG/Threads 帳號設定 + 匿名原則）
  - `AI-Checkpoint.md` 已補 U1 收工紀錄
  - `CLAUDE/工作日誌.md` 已更新

## 下次從這裡接手
- **戰略依據**：一切先看 `我的思維框架/白熊資產地圖 v1.md` 與 `Life OS 營銷總控台.md`
- **Codex 待辦看板**（詳見營銷總控台）：
  - V1：YouTube Pipeline 建設（5 個 Python 腳本）
  - V2：EP1 簡報生成（NotebookLM studio_create）
  - M1：圖卡生成系統 / M2：Google Form Email / M3：NotebookLM 素材輪播
- **已完成待確認**：
  - U2：`link.html` 精簡 link-in-bio 頁，已推送後可在 GitHub Pages 檢查
- **進行中**：用戶正在設定白熊 IG / Threads 帳號（匿名品牌帳號，狀態見 SOP 檔）

## 未完成但已 push 的 WIP
- `8349260`：`WIP: 加入 Week 1 數據追蹤表`
- D1-D4 工作本 v2 深度重製曾在 `/private/tmp/life-os-d1d3` 暫存 worktree，尚未合併到主工作區。

## 需要 Google Drive 的檔案
- 無。本次收工沒有生成新的 PDF、slide、audio 或私密腳本。

## 跨電腦接手分工提醒
- `SESSION.md`（本檔）= repo 內交接單，Codex 維護
- `AI-Checkpoint.md` + `CLAUDE/工作日誌.md` = Obsidian 交接，Claude/使用者維護
- 換電腦開工三步：`git fetch origin` → `git pull origin codex/life-os-mvp` → 讀本檔 + AI-Checkpoint
