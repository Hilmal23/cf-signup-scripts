#!/usr/bin/env python3
"""CF signup via Camoufox with Chromium"""
import sys
sys.path.insert(0, '/root/.cache/camoufox')

from camoufox import Camoufox
import time

PROXY = {'server': 'http://148.72.141.11:9000',
          'username': 'geonode_RTwCdAt5Br-type-residential-country-us',
          'password': '34c063a6-055f-42e0-980d-57db761b8c46'}

print("Starting Camoufox (Chromium)...", flush=True)
with Camoufox(headless=True, humanize=True, geoip=False, proxy=PROXY, browser='chromium') as browser:
    ctx = browser.new_context()
    page = ctx.new_page()

    print("Navigating...", flush=True)
    page.goto('https://dash.cloudflare.com/sign-up', timeout=45000)

    for i in range(30):
        time.sleep(3)
        title = page.title()
        print(f"[{i*3}s] {title[:50]}", flush=True)
        if "Just a moment" not in title:
            break

    print(f"Final: {page.title()} | {page.url}")
    browser.close()