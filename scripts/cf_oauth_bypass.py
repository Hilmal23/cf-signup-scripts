#!/usr/bin/env python3
"""CF OAuth signup test"""
from camoufox import Camoufox
import time

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

with Camoufox(headless=True, geoip=False) as browser:
    ctx = browser.new_context()
    page = ctx.new_page()
    
    page.goto("https://dash.cloudflare.com/sign-up", timeout=60000)
    time.sleep(4)
    
    body = page.inner_text('body')
    if 'let us know' in body.lower():
        log("Challenge shown on load - OAuth won't help")
        page.screenshot(path='/tmp/cf_oauth_check.png')
    else:
        log("No challenge!")
        try:
            page.click('text="Continue with Google"')
            time.sleep(5)
            log(f"After Google click: {page.url} | {page.title()}")
        except Exception as e:
            log(f"Google click error: {e}")
    
    browser.close()

log("=== Done ===")