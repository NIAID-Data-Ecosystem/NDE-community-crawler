#!/usr/bin/env python3
"""
Cloudflare-aware page fetcher for the NDE Community Crawler.

Some approved forums (Biostars, SEQanswers) sit behind Cloudflare's JavaScript
"challenge" mitigation, which plain HTTP clients (curl / WebFetch) cannot pass.
This helper drives a real Chromium via Playwright, which executes the challenge
JS and obtains a cf_clearance cookie. The browser profile is persisted under
.pw-profile/ so the clearance cookie is reused across runs (Cloudflare clearance
typically lasts ~30 min, but the profile also retains other state that reduces
re-challenge frequency).

IMPORTANT: Cloudflare's challenge detects headless Chromium ("HeadlessChrome"
UA and the chromium-headless-shell build). To pass it reliably we run the FULL
Chromium build in *headed* mode, which on a server requires a virtual display.
Always invoke this script through xvfb-run:

    xvfb-run -a python agent/fetch.py <url> [--text|--html] [--timeout SECONDS] [--wait SELECTOR]

Output (stdout): the page content (rendered text by default, or raw HTML).
Exit codes:
    0  success
    2  still blocked by a Cloudflare challenge / CAPTCHA after waiting
    3  navigation error / timeout
    4  bad arguments

Examples:
    python agent/fetch.py "https://www.biostars.org/api/post/?limit=5" --text
    python agent/fetch.py "https://seqanswers.com/" --html --timeout 45
"""

import argparse
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
PROFILE_DIR = REPO_DIR / ".pw-profile"

# A realistic desktop Chrome user-agent. Playwright's default UA contains
# "HeadlessChrome", which Cloudflare flags immediately.
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

# Markers that indicate we're still sitting on a Cloudflare interstitial.
CHALLENGE_MARKERS = (
    "Just a moment...",
    "cf-browser-verification",
    "challenge-platform",
    "Checking your browser",
    "cf_chl_opt",
)


def looks_like_challenge(content: str) -> bool:
    return any(marker in content for marker in CHALLENGE_MARKERS)


def fetch(url: str, mode: str, timeout: float, wait_selector: str | None) -> tuple[int, str]:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    from playwright_stealth import Stealth

    PROFILE_DIR.mkdir(exist_ok=True)
    timeout_ms = int(timeout * 1000)

    # Stealth().use_sync wraps the Playwright driver so every page gets the full
    # suite of automation-evasion patches. Hand-rolled init scripts are NOT
    # enough to clear current Cloudflare challenges; this package is.
    with Stealth().use_sync(sync_playwright()) as p:
        # Persistent context => keeps cookies (incl. cf_clearance) between runs.
        # headless=False + the full Chromium build (not headless-shell) is what
        # gets us past Cloudflare; run under xvfb-run for the virtual display.
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            channel="chromium",
            user_agent=USER_AGENT,
            viewport={"width": 1280, "height": 800},
            locale="en-US",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )
        page = context.new_page()
        try:
            page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")

            # If we hit a Cloudflare challenge, it resolves itself by navigating
            # to the real page. Give it time and poll until the markers clear.
            deadline_left = timeout_ms
            while deadline_left > 0:
                body = page.content()
                if not looks_like_challenge(body):
                    break
                page.wait_for_timeout(2000)
                deadline_left -= 2000
            else:
                return 2, page.content()

            if wait_selector:
                try:
                    page.wait_for_selector(wait_selector, timeout=min(timeout_ms, 15000))
                except PWTimeout:
                    pass  # best-effort; return whatever we have

            if mode == "html":
                content = page.content()
            else:
                content = page.inner_text("body")

            if looks_like_challenge(content):
                return 2, content
            return 0, content
        except PWTimeout:
            return 3, f"Navigation timeout after {timeout}s for {url}"
        except Exception as exc:  # noqa: BLE001 - surface any driver error to caller
            return 3, f"Navigation error for {url}: {exc}"
        finally:
            context.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Cloudflare-aware page fetcher.")
    parser.add_argument("url")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--text", action="store_const", dest="mode", const="text")
    group.add_argument("--html", action="store_const", dest="mode", const="html")
    parser.add_argument("--timeout", type=float, default=45.0,
                        help="Max seconds for navigation + challenge solve (default 45).")
    parser.add_argument("--wait", dest="wait_selector", default=None,
                        help="Optional CSS selector to wait for before reading.")
    parser.set_defaults(mode="text")
    args = parser.parse_args()

    code, content = fetch(args.url, args.mode, args.timeout, args.wait_selector)
    if code == 2:
        sys.stderr.write(
            "BLOCKED: Cloudflare challenge/CAPTCHA not cleared. "
            "Site may have escalated to a managed challenge.\n"
        )
    elif code == 3:
        sys.stderr.write(content + "\n")
        return 3
    sys.stdout.write(content)
    return code


if __name__ == "__main__":
    sys.exit(main())
