#!/usr/bin/env python3
"""CF signup via Playwright Chromium - wait for challenge"""
from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context()
    page = ctx.new_page()

    print("Navigating to CF signup...")
    page.goto("https://dash.cloudflare.com/sign-up", timeout=45000)
    print(f"Initial URL: {page.url}")

    # Wait for challenge to resolve
    for i in range(30):
        time.sleep(3)
        url = page.url
        title = page.title()
        print(f"[{i*3}s] Title: {title[:60]}")

        if "Just a moment" not in title:
            break
    else:
        print("Challenge TIMEOUT after 90s")

    print(f"\nFinal Title: {page.title()}")
    print(f"Final URL: {page.url}")

    inputs = page.query_selector_all("input")
    print(f"Inputs found: {len(inputs)}")

    body = page.inner_text("body")[:600]
    print(f"Body: {body}")

    browser.close()