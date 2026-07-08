#!/usr/bin/env python3
"""CF signup - test WITHOUT proxy first"""
from camoufox import Camoufox
import time

with Camoufox(headless=True, humanize=True, geoip=False) as browser:
    ctx = browser.new_context()
    page = ctx.new_page()

    print("Navigating to CF signup (no proxy)...")
    page.goto('https://dash.cloudflare.com/sign-up', timeout=45000)
    print(f"Initial URL: {page.url}")

    # Wait for challenge
    for i in range(20):
        time.sleep(3)
        title = page.title()
        print(f"[{i*3}s] {title[:60]}", flush=True)
        if "Just a moment" not in title:
            break

    print(f"\nFinal: {page.title()} | {page.url}")
    inputs = page.query_selector_all("input")
    print(f"Inputs: {len(inputs)}")

    body = page.inner_text("body")[:400]
    print(f"Body: {body}")

    browser.close()