#!/usr/bin/env python3
from camoufox import Camoufox
import time

with Camoufox(headless=True, humanize=True, geoip=False) as browser:
    ctx = browser.new_context(locale='en-US', viewport={'width': 1280, 'height': 720})
    ctx.clear_cookies()
    page = ctx.new_page()
    
    print("Navigating...")
    page.goto('https://dash.cloudflare.com/sign-up', wait_until='domcontentloaded', timeout=30000)
    print("Title after goto:", page.title())
    
    for i in range(20):
        time.sleep(3)
        title = page.title()
        content = page.content()[:200]
        print("[%ds] Title: %s | Content preview: %s" % ((i+1)*3, title, content[:100]))
        if 'Just a moment' not in title:
            print("NOT 'Just a moment' - breaking")
            break
    
    print("\nFinal URL:", page.url)
    print("Final Title:", page.title())
    print("Final Content:", page.content()[:500])
    
    browser.close()