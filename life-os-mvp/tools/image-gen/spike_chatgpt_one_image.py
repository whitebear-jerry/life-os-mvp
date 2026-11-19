#!/usr/bin/env python3
"""One-shot ChatGPT image-generation spike via a logged-in Chrome profile.

This is intentionally small and disposable: it opens ChatGPT in headed Chrome,
posts one prompt, waits for one generated image, and saves a PNG screenshot of
that image to /tmp/spike-output.png by default.
"""

from __future__ import annotations

import argparse
import base64
import shutil
import time
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


DEFAULT_PROMPT = '畫一隻可愛的 3D 卡通白熊舉著寫著 "EP3 spike" 的旗子，藍色漸層背景，16:9'
DEFAULT_PROFILE = Path("~/Library/Application Support/Google/Chrome/Default").expanduser()
DEFAULT_PROFILE_COPY = Path("/private/tmp/codex-chatgpt-chrome-profile")
DEFAULT_OUTPUT = Path("/tmp/spike-output.png")
CHATGPT_URL = "https://chatgpt.com/"
LOCK_FILES = ("SingletonLock", "SingletonCookie", "SingletonSocket")
PROFILE_COPY_SKIP_NAMES = {
    "BrowserMetrics",
    "Cache",
    "CachedData",
    "Code Cache",
    "Crashpad",
    "DawnCache",
    "GPUCache",
    "GraphiteDawnCache",
    "GrShaderCache",
    "OptimizationHints",
    "Safe Browsing",
    "ShaderCache",
    "SingletonCookie",
    "SingletonLock",
    "SingletonSocket",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="One-shot ChatGPT image generation spike.")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT, help="Prompt to paste into ChatGPT.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output PNG path. Default: /tmp/spike-output.png")
    parser.add_argument(
        "--chrome-profile",
        type=Path,
        default=DEFAULT_PROFILE,
        help="Chrome profile directory, usually ~/Library/Application Support/Google/Chrome/Default",
    )
    parser.add_argument("--timeout", type=int, default=180, help="Max seconds to wait for a generated image. Default: 180")
    parser.add_argument(
        "--manual-gate-timeout",
        type=int,
        default=180,
        help="Seconds to wait for manual login or human-verification steps before looking for the composer. Default: 180",
    )
    parser.add_argument("--url", default=CHATGPT_URL, help="ChatGPT URL. Default: https://chatgpt.com/")
    parser.add_argument("--channel", default="chrome", help="Playwright browser channel. Default: chrome")
    parser.add_argument(
        "--profile-mode",
        choices=("clone", "direct"),
        default="clone",
        help=(
            "Use a temporary copy of the Chrome profile, or launch the original profile directly. "
            "Default: clone, because recent Chrome blocks remote debugging against the default profile."
        ),
    )
    parser.add_argument(
        "--profile-copy-dir",
        type=Path,
        default=DEFAULT_PROFILE_COPY,
        help=f"Temporary Chrome user data dir for --profile-mode clone. Default: {DEFAULT_PROFILE_COPY}",
    )
    parser.add_argument(
        "--reuse-profile-copy",
        action="store_true",
        help="Reuse --profile-copy-dir instead of refreshing it from the source Chrome profile.",
    )
    parser.add_argument("--keep-open", action="store_true", help="Keep the browser open after the spike finishes.")
    parser.add_argument("--ignore-profile-lock", action="store_true", help="Proceed even if Chrome profile lock files exist.")
    return parser


def resolve_chrome_profile(profile_dir: Path) -> tuple[Path, str | None]:
    profile_dir = profile_dir.expanduser().resolve()
    user_data_dir = profile_dir.parent
    profile_name = profile_dir.name
    if profile_name in {"Default"} or profile_name.startswith("Profile "):
        return user_data_dir, profile_name
    return profile_dir, None


def check_profile_lock(user_data_dir: Path, ignore_lock: bool) -> None:
    locks = [user_data_dir / name for name in LOCK_FILES if (user_data_dir / name).exists()]
    print("提醒：請先完全關閉本機 Google Chrome，再跑這個 spike；否則登入 profile 可能被鎖。")
    print("提醒：這個 spike 只送出一張圖的 prompt，不做批次、不重試。")
    if not locks:
        return
    lock_list = "\n".join(f"- {path}" for path in locks)
    message = (
        "Chrome profile 看起來正在使用中，為了避免破壞登入態，先停下。\n"
        f"偵測到 lock 檔：\n{lock_list}\n"
        "請關閉 Chrome 後再跑；若你確認是 stale lock，可加 --ignore-profile-lock。"
    )
    if ignore_lock:
        print("⚠️ " + message)
        return
    raise SystemExit(message)


def should_skip_profile_copy(directory: str, names: list[str]) -> set[str]:
    skipped = {name for name in names if name in PROFILE_COPY_SKIP_NAMES or name.endswith("-journal")}
    if Path(directory).name == "Service Worker":
        skipped.update({"CacheStorage", "ScriptCache"})
    return skipped


def prepare_user_data_dir(args) -> tuple[Path, str | None, Path]:
    source_user_data_dir, profile_name = resolve_chrome_profile(args.chrome_profile)
    check_profile_lock(source_user_data_dir, args.ignore_profile_lock)

    if args.profile_mode == "direct":
        return source_user_data_dir, profile_name, source_user_data_dir

    if not profile_name:
        raise SystemExit("--profile-mode clone 需要 --chrome-profile 指到 Default 或 Profile N 這類 Chrome profile 目錄。")

    copy_user_data_dir = args.profile_copy_dir.expanduser().resolve()
    source_profile_dir = source_user_data_dir / profile_name
    target_profile_dir = copy_user_data_dir / profile_name
    if not source_profile_dir.exists():
        raise SystemExit(f"找不到來源 Chrome profile：{source_profile_dir}")

    if copy_user_data_dir.exists() and not args.reuse_profile_copy:
        shutil.rmtree(copy_user_data_dir)
    copy_user_data_dir.mkdir(parents=True, exist_ok=True)

    if not args.reuse_profile_copy or not target_profile_dir.exists():
        print(f"Copying Chrome profile to temporary user data dir: {copy_user_data_dir}")
        local_state = source_user_data_dir / "Local State"
        if local_state.exists():
            shutil.copy2(local_state, copy_user_data_dir / "Local State")
        shutil.copytree(
            source_profile_dir,
            target_profile_dir,
            dirs_exist_ok=True,
            ignore=should_skip_profile_copy,
        )
    else:
        print(f"Reusing existing temporary profile copy: {copy_user_data_dir}")

    return copy_user_data_dir, profile_name, source_user_data_dir


def visible_composer(page, manual_gate_timeout: int):
    selectors = [
        "[data-testid='prompt-textarea']",
        "#prompt-textarea",
        "textarea[placeholder*='Message']",
        "textarea",
        "div[contenteditable='true']",
    ]
    deadline = time.monotonic() + manual_gate_timeout
    prompted_for_manual_gate = False
    while time.monotonic() < deadline:
        for selector in selectors:
            locator = page.locator(selector).last
            try:
                locator.wait_for(state="visible", timeout=2_000)
                return locator, selector
            except PlaywrightTimeoutError:
                continue
        if not prompted_for_manual_gate:
            print(
                "ChatGPT composer 尚未出現；若瀏覽器顯示人類驗證或登入確認，請手動完成，腳本會繼續等待。",
                flush=True,
            )
            prompted_for_manual_gate = True
        page.wait_for_timeout(3_000)
    raise RuntimeError("找不到 ChatGPT prompt 輸入框，可能尚未登入或 UI 已改版。")


def image_candidates_script() -> str:
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
          item.nh >= 256 &&
          item.rw >= 180 &&
          item.rh >= 120
        );
    }
    """


def collect_image_sources(page) -> list[str]:
    return page.evaluate(
        """() => Array.from(document.images).map(img => img.currentSrc || img.src || "").filter(Boolean)"""
    )


def find_generated_image(page, known_sources: list[str], timeout_ms: int):
    page.wait_for_function(
        """({ knownSources, candidatesScript }) => {
          const candidates = eval(candidatesScript)(knownSources);
          return candidates.length > 0;
        }""",
        arg={"knownSources": known_sources, "candidatesScript": image_candidates_script()},
        timeout=timeout_ms,
    )
    handle = page.evaluate_handle(
        """({ knownSources, candidatesScript }) => {
          const candidates = eval(candidatesScript)(knownSources);
          return candidates[0].img;
        }""",
        {"knownSources": known_sources, "candidatesScript": image_candidates_script()},
    )
    return handle.as_element()


def try_fetch_image_bytes(page, image_handle) -> tuple[bytes | None, str | None]:
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
            image_handle,
        )
        return base64.b64decode(payload["data"]), str(payload["mime"])
    except PlaywrightError as exc:
        print(f"直接抓 image src 失敗，改用元素截圖保存 PNG：{exc}")
        return None, None


def save_generated_image(page, image_handle, output_path: Path) -> str:
    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data, mime = try_fetch_image_bytes(page, image_handle)
    if data and mime == "image/png":
        output_path.write_bytes(data)
        return f"downloaded source bytes ({mime})"

    image_handle.screenshot(path=str(output_path))
    if data:
        raw_path = output_path.with_suffix(".source")
        raw_path.write_bytes(data)
        return f"element screenshot PNG; also saved source bytes ({mime}) to {raw_path}"
    return "element screenshot PNG"


def main() -> None:
    args = build_parser().parse_args()
    start_time = time.monotonic()
    user_data_dir, profile_name, source_user_data_dir = prepare_user_data_dir(args)

    launch_args = []
    if profile_name:
        launch_args.append(f"--profile-directory={profile_name}")

    print(f"Source Chrome user data dir: {source_user_data_dir}")
    print(f"Playwright Chrome user data dir: {user_data_dir}")
    if profile_name:
        print(f"Chrome profile: {profile_name}")
    print(f"Output: {args.output}")

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            channel=args.channel,
            headless=False,
            accept_downloads=True,
            viewport={"width": 1440, "height": 1100},
            args=launch_args,
        )
        page = context.pages[0] if context.pages else context.new_page()
        try:
            print("Opening ChatGPT...")
            page.goto(args.url, wait_until="domcontentloaded", timeout=60_000)
            composer, selector = visible_composer(page, args.manual_gate_timeout)
            print(f"Composer selector: {selector}")

            known_sources = collect_image_sources(page)
            print(f"Initial image sources observed: {len(known_sources)}")

            composer.click()
            page.keyboard.insert_text(args.prompt)
            page.keyboard.press("Enter")
            print("Prompt submitted; waiting for generated image...")

            image_handle = find_generated_image(page, known_sources, timeout_ms=args.timeout * 1000)
            mode = save_generated_image(page, image_handle, args.output)
            elapsed = time.monotonic() - start_time
            print(f"✅ Success: saved {args.output} via {mode}")
            print(f"Elapsed seconds: {elapsed:.1f}")
        except Exception as exc:
            debug_png = args.output.with_name(args.output.stem + "-debug.png")
            debug_txt = args.output.with_name(args.output.stem + "-debug.txt")
            try:
                page.screenshot(path=str(debug_png), full_page=True)
                debug_txt.write_text(page.locator("body").inner_text(timeout=3_000), encoding="utf-8")
                print(f"Debug screenshot: {debug_png}")
                print(f"Debug DOM text: {debug_txt}")
            except Exception as debug_exc:
                print(f"Debug capture failed: {debug_exc}")
            raise SystemExit(f"❌ Spike failed: {exc}") from exc
        finally:
            if args.keep_open:
                print("Keeping browser open because --keep-open was set.")
            else:
                context.close()


if __name__ == "__main__":
    main()
