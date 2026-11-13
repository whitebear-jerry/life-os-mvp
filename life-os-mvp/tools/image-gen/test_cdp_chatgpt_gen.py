#!/usr/bin/env python3
"""
CDP (Chrome DevTools Protocol) ChatGPT Image Generation Test Tool.
This script connects to an already running, logged-in Chrome instance at port 9222,
types an image generation prompt, waits for the image to be created by DALL-E,
and saves the result. This bypasses Cloudflare bot protection entirely.
"""

import sys
import time
import base64
from pathlib import Path
from playwright.sync_api import sync_playwright, Error as PlaywrightError

CDP_URL = "http://127.0.0.1:9222"
DEFAULT_PROMPT = "畫一隻可愛的 3D 卡通白熊舉著寫著 'CDP Test Success!' 的黃色旗子，降噪藍漸層背景，16:9，畫中除旗子外不要任何文字"
DEFAULT_OUTPUT = Path("/Users/baizhewei/Library/CloudStorage/GoogleDrive-0927136551jerry@gmail.com/我的雲端硬碟/Life OS/marketing/season1-降噪人生/episode-03-第二大腦-Notion-外接硬碟/images/cdp-test-success.png")

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

def find_generated_image(page, known_sources: list[str], timeout_sec: int):
    """Polls the page until a new generated image element is discovered."""
    print(f"⏳ 正在等待 DALL-E 繪製生成圖片 (最長等待 {timeout_sec} 秒)...")
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
    raise TimeoutError("等待生圖超時，請檢查 ChatGPT 網頁是否生成完畢。")

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
        print(f"📥 成功透過 fetch 原始位元組下載並存檔：{output_path}")
        return
    except Exception as exc:
        print(f"⚠️ 直接下載圖片位元組失敗 ({exc})，改用 Playwright 元素截圖保存...")
        try:
            image_element.screenshot(path=str(output_path))
            print(f"📸 成功以元素截圖方式存檔：{output_path}")
        except Exception as screenshot_exc:
            raise RuntimeError(f"所有存檔管道皆失敗: {screenshot_exc}")

def main():
    print("🚀 啟動 CDP ChatGPT 遠端連接生圖測試腳本 🚀\n")
    print(f"🔗 預設目標埠口: {CDP_URL}")
    print(f"🎯 測試提示詞: '{DEFAULT_PROMPT}'")
    print(f"💾 輸出路徑: {DEFAULT_OUTPUT}\n")
    
    with sync_playwright() as playwright:
        try:
            # Connect to already running Chrome
            print("📡 正在嘗試連線至本機已開的 Chrome (port 9222)...")
            browser = playwright.chromium.connect_over_cdp(CDP_URL)
        except PlaywrightError as err:
            print("\n❌ 連線失敗！請確認：")
            print("1. 您已完全關閉普通的 Chrome 視窗 (Cmd + Q)。")
            print("2. 您已在終端機運行以下指令開啟 Debug 版 Chrome:")
            print("   /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222")
            print(f"\n錯誤詳情: {err}")
            sys.exit(1)
            
        try:
            # Connect to context
            context = browser.contexts[0]
            page = find_chatgpt_page(context)
            
            # Activate tab and wait a bit
            page.bring_to_front()
            page.wait_for_timeout(2000)
            
            # Find input box
            print("🔍 尋找輸入框...")
            composer, selector = get_visible_composer(page)
            print(f"✅ 成功找到輸入框 (Selector: {selector})")
            
            # Record current images on page to detect new ones later
            known_sources = collect_image_sources(page)
            print(f"📊 當前頁面已有圖片數: {len(known_sources)}")
            
            # Type prompt
            print("⌨️ 正在貼入測試生圖提示詞...")
            composer.click()
            page.keyboard.insert_text(DEFAULT_PROMPT)
            page.wait_for_timeout(1000)
            
            # Press enter
            print("🚀 送出提示詞！")
            page.keyboard.press("Enter")
            
            # Wait for image to generate
            image_element = find_generated_image(page, known_sources, timeout_sec=120)
            
            # Save the image
            save_image(page, image_element, DEFAULT_OUTPUT)
            print(f"\n🎉 測試成功！請至桌面查看生圖結果：[cdp-test-success.png]")
            
        except Exception as exc:
            print(f"\n❌ 測試執行出錯: {exc}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
