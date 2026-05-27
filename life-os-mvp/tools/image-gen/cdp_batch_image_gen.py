#!/usr/bin/env python3
"""
CDP (Chrome DevTools Protocol) ChatGPT Batch Image Generator.
This script reads the image-prompts.md file in the EP03 GDrive directory,
connects to the running Chrome instance at port 9222,
submits the style anchor, then generates, downloads, and saves
each image to the correct local GDrive images/ directory.
"""

import os
import re
import sys
import time
import base64
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright, Error as PlaywrightError

CDP_URL = "http://127.0.0.1:9222"
EP03_DIR = Path("/Users/baizhewei/Library/CloudStorage/GoogleDrive-0927136551jerry@gmail.com/我的雲端硬碟/Life OS/marketing/season1-降噪人生/episode-03-第二大腦-Notion-外接硬碟")
PROMPTS_FILE = EP03_DIR / "image-prompts.md"
IMAGES_DIR = EP03_DIR / "images"

def parse_prompts(prompts_file_path: Path) -> dict:
    """Parses style anchors and individual image specs from the markdown file."""
    if not prompts_file_path.exists():
        raise FileNotFoundError(f"找不到提示詞輸入檔: {prompts_file_path}")
        
    content = prompts_file_path.read_text(encoding="utf-8")
    
    # Parse Style Anchor
    style_match = re.search(r"風格錨點:\s*(.+)", content)
    style_anchor = style_match.group(1).strip() if style_match else ""
    
    # Parse individual image blocks
    # Looking for blocks starting with - 檔名: story-X.png
    image_specs = []
    blocks = content.split("- 檔名:")
    for block in blocks[1:]:
        lines = block.strip().split("\n")
        filename = lines[0].strip()
        
        prompt = ""
        type_str = ""
        for line in lines[1:]:
            line_strip = line.strip()
            if line_strip.startswith("類型:"):
                type_str = line_strip.replace("類型:", "").strip()
            elif line_strip.startswith("提示詞:"):
                prompt = line_strip.replace("提示詞:", "").strip()
                # If prompt spreads across multiple lines (yaml block style)
                idx = lines.index(line)
                if prompt == "|" or prompt == "":
                    prompt = "\n".join(l.strip() for l in lines[idx+1:] if l.strip() and not l.strip().startswith("-"))
        
        if filename and prompt:
            image_specs.append({
                "filename": filename,
                "type": type_str,
                "prompt": prompt.strip()
            })
            
    return {
        "style_anchor": style_anchor,
        "images": image_specs
    }

def find_chatgpt_page(context):
    """Finds an existing ChatGPT tab, or opens a new one if not found."""
    for page in context.pages:
        url = page.url
        if "chatgpt.com" in url:
            print(f"📡 發現已開啟的 ChatGPT 頁面: {url}")
            return page
    
    print("📡 未偵測到 chatgpt.com 分頁，正在開啟新分頁...")
    page = context.new_page()
    page.goto("https://chatgpt.com", wait_until="domcontentloaded")
    return page

def get_visible_composer(page):
    """Finds the ChatGPT text area input element."""
    selectors = [
        "[data-testid='prompt-textarea']",
        "#prompt-textarea",
        "textarea[placeholder*='Message']",
        "textarea",
        "div[contenteditable='true']"
    ]
    for selector in selectors:
        locator = page.locator(selector).last
        if locator.is_visible():
            return locator, selector
    raise RuntimeError("找不到 ChatGPT prompt 輸入框，請確認網頁已加載完畢且已登入！")

def collect_image_sources(page) -> list[str]:
    """Collects all image URLs currently loaded on the page."""
    try:
        return page.evaluate(
            """() => Array.from(document.images).map(img => img.currentSrc || img.src || "").filter(Boolean)"""
        )
    except Exception:
        return []

def image_candidates_script() -> str:
    """JS script to filter DALL-E generated image elements."""
    return """
    (knownSources) => {
      const known = new Set(knownSources);
      const badSrc = /(avatar|favicon|openai|logo|sprite|backend-api\\/models)/i;
      return Array.from(document.images)
        .map((img, index) => {
          const rect = img.getBoundingClientRect();
          const src = img.currentSrc || img.src || "";
          return { img, index, src, alt: img.alt || "", nw: img.naturalWidth, nh: img.naturalHeight, rw: rect.width, rh: rect.height };
        })
        .filter(item =>
          item.src &&
          !known.has(item.src) &&
          !badSrc.test(item.src) &&
          item.nw >= 256 &&
          item.nh >= 256
        );
    }
    """

def find_generated_image(page, known_sources: list[str], filename: str, timeout_sec: int):
    """Polls the page until a new generated image element is discovered."""
    print(f"⏳ 正在等待 DALL-E 繪製 [{filename}] (最長等待 {timeout_sec} 秒)...")
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        try:
            has_new = page.evaluate(
                """({ knownSources, candidatesScript }) => {
                  const candidates = eval(candidatesScript)(knownSources);
                  return candidates.length > 0;
                }""",
                {"knownSources": known_sources, "candidatesScript": image_candidates_script()}
            )
            if has_new:
                # Find and return the element handle
                handle = page.evaluate_handle(
                    """({ knownSources, candidatesScript }) => {
                      const candidates = eval(candidatesScript)(knownSources);
                      return candidates[0].img;
                    }""",
                    {"knownSources": known_sources, "candidatesScript": image_candidates_script()}
                )
                return handle.as_element()
        except Exception:
            pass
        page.wait_for_timeout(2000)
    raise TimeoutError(f"等待生圖 [{filename}] 超時，請確認 ChatGPT 網頁是否生成完畢。")

def save_image(page, image_element, output_path: Path):
    """Saves the image by fetching its src bytes directly, falling back to element screenshot."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        payload = page.evaluate(
            """async (img) => {
              const src = img.currentSrc || img.src;
              const response = await fetch(src);
              const blob = await response.blob();
              const buffer = await blob.arrayBuffer();
              let binary = "";
              const bytes = new Uint8Array(buffer);
              for (let i = 0; i < bytes.byteLength; i++) binary += String.fromCharCode(bytes[i]);
              return { mime: blob.type || "application/octet-stream", data: btoa(binary) };
            }""",
            image_element
        )
        data = base64.b64decode(payload["data"])
        output_path.write_bytes(data)
        print(f"📥 成功下載原始圖片位元組並儲存：{output_path}")
        return True
    except Exception as exc:
        print(f"⚠️ 直接下載原始位元組失敗 ({exc})，改用 Playwright 元素畫布截圖保存...")
        try:
            image_element.screenshot(path=str(output_path))
            print(f"📸 成功以元素截圖方式存檔：{output_path}")
            return True
        except Exception as screenshot_exc:
            print(f"❌ 存檔所有管道皆失敗: {screenshot_exc}")
            return False

def submit_prompt(page, prompt_text: str):
    """Focuses the composer, types the text, and submits the message."""
    composer, selector = get_visible_composer(page)
    composer.click()
    page.keyboard.insert_text(prompt_text)
    page.wait_for_timeout(1000)
    page.keyboard.press("Enter")

def main():
    parser = argparse.ArgumentParser(description="Batch CDP Image Generator")
    parser.add_argument("--skip", type=int, default=0, help="Skip the first N images in markdown.")
    args = parser.parse_args()

    print("🚀 啟動 CDP ChatGPT 批次自動生圖與歸位程序 🚀\n")
    print(f"📂 專案輸入檔: {PROMPTS_FILE}")
    print(f"📂 圖片輸出路徑: {IMAGES_DIR}\n")
    
    # Parse markdown file
    try:
        specs = parse_prompts(PROMPTS_FILE)
        print(f"✅ 成功解析提示詞！")
        print(f"🎨 全片風格鎖定: {specs['style_anchor'][:60]}...")
        print(f"📊 待生圖總數: {len(specs['images'])} 張")
    except Exception as e:
        print(f"❌ 解析 markdown 失敗: {e}")
        sys.exit(1)
        
    with sync_playwright() as playwright:
        try:
            print("\n📡 正在嘗試連線至本機已開的 Chrome (port 9222)...")
            browser = playwright.chromium.connect_over_cdp(CDP_URL)
        except PlaywrightError as err:
            print("\n❌ 連線失敗！請確認：")
            print("1. 您已啟動 Debug 版 Chrome: /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222 --user-data-dir=\".../Default_CDP\"")
            print("2. 瀏覽器視窗開啟了且您已手動進入 chatgpt.com 當前對話分頁。")
            print(f"\n錯誤詳情: {err}")
            sys.exit(1)
            
        try:
            context = browser.contexts[0]
            page = find_chatgpt_page(context)
            page.bring_to_front()
            page.wait_for_timeout(2000)
            
            # Setup Style Anchor first (Only if not skipping)
            if args.skip == 0:
                print("\n📌 Step 1: 正在提交全片風格鎖定錨點與角色設定...")
                anchor_prompt = f"接下來我需要你生成一系列影片插畫。這是全片統一的風格鎖定錨點，請牢記：\n\n『{specs['style_anchor']}』\n\n請以『收到風格設定。請發送第一張圖的提示詞。』簡短回覆，不要生成圖片。"
                submit_prompt(page, anchor_prompt)
                print("⏳ 正在等待 ChatGPT 回應風格確認...")
                page.wait_for_timeout(8000)
                
            # Iterate through images
            for idx, img_spec in enumerate(specs["images"]):
                if idx < args.skip:
                    print(f"⏭️ 略過第 {idx+1} 張圖片: {img_spec['filename']}")
                    continue
                    
                print(f"\n🎨 Step {idx+1}/{len(specs['images'])}: 正在生成 [{img_spec['filename']}]...")
                print(f"💬 提示詞: {img_spec['prompt'][:80]}...")
                
                # Gather current images to detect the newly generated one
                known_sources = collect_image_sources(page)
                
                # Submit image prompt
                submit_prompt(page, img_spec["prompt"])
                print("🚀 提示詞已提交，等待 ChatGPT DALL-E 生圖中...")
                
                # Wait and discover image
                try:
                    img_element = find_generated_image(page, known_sources, img_spec["filename"], timeout_sec=180)
                    output_path = IMAGES_DIR / img_spec["filename"]
                    
                    # Save image
                    success = save_image(page, img_element, output_path)
                    if success:
                        print(f"✅ [{img_spec['filename']}] 儲存歸位成功！")
                    else:
                        print(f"❌ [{img_spec['filename']}] 存檔失敗！")
                except Exception as gen_err:
                    print(f"❌ 生成 [{img_spec['filename']}] 出錯: {gen_err}")
                    print("⚠️ 略過此張，繼續生成下一張...")
                
                # Politeness sleep between generations
                print("⏸️ 禮貌性等待 5 秒，防止被 ChatGPT 限速...")
                page.wait_for_timeout(5000)
                
            print("\n🎉 批量自動生圖與 GDrive 歸位大功告成！🎉")
            
        except Exception as exc:
            print(f"\n❌ 批次執行出錯: {exc}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
