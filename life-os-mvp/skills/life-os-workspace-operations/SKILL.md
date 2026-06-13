---
name: life-os-workspace-operations
description: >
  Guidelines and workflows for managing the White Bear Life OS MVP codebase,
  including website deployment, video processing pipeline, and RPG minigame logic.
---

# Life OS Workspace Operations

This skill documents and packages all the developer workflows and operational logic for the "白熊的人生演算法書房" (White Bear Life OS MVP) project. Use this skill when checking out the project on a new computer to continue development, run scripts, or perform deployments.

## 1. Project Overview & Architecture

The workspace consists of a static marketing website (`index.html`, `link.html`, `freebie.html`), a JRPG-style gamified learning engine, and background utility scripts:
*   **Production Environment (`gh-pages` branch)**: Served at the repository root level. The live site builds from this branch.
*   **Development Environment (`codex/life-os-mvp` branch)**: Code is structured inside the `life-os-mvp/` subdirectory.

## 2. Core Workflows

### A. Code Synchronization & Deployment
When modifying the website, always ensure changes are deployed to the live site and synced back to development:

1.  **Deploying to Live Site (`gh-pages`)**:
    *   Stash any local changes on the development branch: `git stash`.
    *   Switch to `gh-pages`: `git checkout gh-pages`.
    *   Make edits to root files (e.g., `index.html`, `link.html`, `assets/styles.css`).
    *   Commit and push: `git add . && git commit -m "commit message" && git push origin gh-pages`.

2.  **Syncing back to Development (`codex/life-os-mvp`)**:
    *   Switch to development branch: `git checkout codex/life-os-mvp`.
    *   Pop the stash: `git stash pop`.
    *   Bring updated files from `gh-pages` into the `life-os-mvp/` subdirectory:
        ```bash
        git checkout gh-pages -- index.html link.html assets/styles.css
        mv index.html life-os-mvp/index.html
        mv link.html life-os-mvp/link.html
        mv assets/styles.css life-os-mvp/assets/styles.css
        git restore --staged index.html link.html assets/styles.css
        ```
    *   Commit the synced changes: `git add life-os-mvp/ && git commit -m "sync with production" && git push origin codex/life-os-mvp`.

### B. Video Processing Pipeline
The workspace contains a python-based pipeline to transcribe, correct, and slice video episodes under `tools/video-pipeline/`:
*   **Duplicate Cut Detection**: Analyzes segments to find adjacent NG takes and automatically slice them out using FFmpeg.
*   **Subtitles and Transcription**: Corrects transcriptions using `vocab.json` mapping.

**How to Run**:
*   Always use `uv` package manager:
    ```bash
    uv run tools/video-pipeline/episode-pipeline.py
    uv run tools/video-pipeline/trim-duplicates.py
    ```

### C. Marketing & Pricing Configurations
When updating pricing in `index.html` or `link.html`, always maintain the correct pricing structure:
*   **《人生複利》**: 原價 $220, 特價 $149 (67折, 省 $71)
*   **《人生遊戲》**: 原價 $280, 特價 $199 (71折, 省 $81)
*   **《降噪人生》**: 原價 $360, 特價 $269 (74折, 省 $91)
*   **3冊合購套書特惠包**: 原價 $860, 特價 $499 (58折, 省 $361)
*   **Affiliate Tracking**: Outbound links to Pubu must contain the affiliate key: `apKey=e08e864a73`.
*   **Bundle Image**: Always use `assets/book_bundle.jpg` for the 3-book bundle display.

### D. JRPG Gamification Engine
*   Located in `assets/rpg-engine.js` (loaded by `link.html`).
*   Configured with dynamic monster scaling (`bossHp`, `bossAtk`, `bossDef`) and focus-based action triggers to represent learning productivity.

---

## 3. Google Drive Backup Reference
A zipped archive of this workspace and the git repository is backed up at:
`Google Drive/我的雲端硬碟/Life OS/workspace_backup/`
