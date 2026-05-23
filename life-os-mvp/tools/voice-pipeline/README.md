# voice-pipeline（F5-TTS 聲音克隆）

> ⏸️ 目前暫停使用（改用螢幕錄影模式錄旁白）。保留環境，未來要重啟可立即用。

## 這資料夾在做什麼

用 F5-TTS 做中文聲音克隆：給一段參考音檔 + 文字 → 生成同音色的旁白。

## ⚠️ venv 不進 git（每台電腦自建）

`.venv-f5tts/` 有 1.7GB（PyTorch 等），已被 `.gitignore` 排除。
換電腦要用時，重建環境：

```bash
cd tools/voice-pipeline
/opt/homebrew/bin/python3.11 -m venv .venv-f5tts
source .venv-f5tts/bin/activate
pip install f5-tts          # 首次會自動下載 ~1.5GB 模型到 ~/.cache/huggingface/
```

## 用法（CLI）

```bash
source .venv-f5tts/bin/activate
f5-tts_infer-cli \
  --model F5TTS_v1_Base \
  --ref_audio "samples/<參考音>.wav" \
  --ref_text "<參考音逐字稿>" \
  --gen_text "<要生成的文字>" \
  --output_dir "outputs" \
  --output_file "out.wav" \
  --device mps
```

## 測試結論（2026-05-18）

- 用 EP1 前 8 秒當參考 → 生成 22 秒測試音
- CPU 約 4 分鐘 / MPS 約 3.5 分鐘（速度偏慢）
- 音色「有點像但不夠像」→ 暫停，改螢幕錄影真人錄

## 資料夾

- `.venv-f5tts/`（gitignore）：Python 環境
- `samples/`（gitignore）：參考音檔
- `outputs/`（gitignore）：生成結果
