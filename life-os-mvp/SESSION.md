# ⚡ Codex Session 協定

**每次開始必讀，每次結束必更新。**

> 核心規則：開始前先 `git pull`，結束前先 `git push`。如果本機有未提交變更，不要硬拉；先使用安全 worktree 或請使用者確認。

## 每次開始前

1. `git fetch origin`
2. `git pull origin <目前分支>`
3. 確認 Google Drive 已掛載：`ls ~/Library/CloudStorage/GoogleDrive-0927136551jerry@gmail.com/我的雲端硬碟/`
4. 讀取 `AI-Checkpoint.md`，了解上一次到哪裡
5. 檢查 `git status --short --branch`，確認目前工作區是否乾淨

## 每次結束前

1. 只 stage 安全檔案：`.md`、`.html`、`.css`、`.js`、`.py`
2. `git commit -m "WIP: <今天做了什麼，一句話>"`
3. `git push origin <目前分支>`
4. 更新 `AI-Checkpoint.md`，寫清楚完成了什麼、下次從哪裡繼續
5. 如果有生成 PDF 或 slide，確認已複製到 Google Drive

## 最近一次 session

- 電腦：Mac.lan
- 日期：2026-05-11
- 分支：codex/life-os-mvp
- 完成：建立兩台電腦同步協定，新增 `SESSION.md` 交接單。
- 下次從：接手時先讀本檔與 `AI-Checkpoint.md`，再確認是否要同步部署最新頁面到 `gh-pages` 或繼續 Claude 審核修正。

## 未完成但已 push 的 WIP

- 目前沒有未完成但已 push 的 C6 程式碼 WIP。
- C1-C5 已 push 到 `codex/life-os-mvp`；`gh-pages` 尚未同步 C1-C5 / C6 的最新主分支內容。

## 需要 Google Drive 的檔案

- 本次 C6 沒有生成 PDF 或 slide。
- 若後續產出 `deliverables/pdf/*.pdf`，請放到 `Google Drive/Life OS/deliverables/pdf/`。
