#!/usr/bin/env python3
"""CF signup - NO waits, fill+submit FAST"""
from camoufox import Camoufox
import time

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

email = f"fast{int(time.time())}@hilmal.store"
pw = "FastPass123!"
log(f"Fast test: {email}")

with Camoufox(headless=True, geoip=False) as browser:
    ctx = browser.new_context()
    page = ctx.new_page()
    
    # Load page
    page.goto("https://dash.cloudflare.com/sign-up", timeout=30000)
    
    # Immediately fill (within 1 second)
    page.fill('input[name="email"]', email)
    page.fill('input[name="password"]', pw)
    
    # Immediately submit
    page.click('button[type="submit"]')
    time.sleep(5)
    
    title = page.title()
    url = page.url
    body = page.inner_text('body')
    
    log(f"Title: {title}")
    log(f"URL: {url}")
    log(f"Body: {body[:200]}")
    
    if 'dashboard' in title.lower() and 'sign-up' not in url:
        log("SUCCESS! Dashboard loaded!")
        page.screenshot(path='/tmp/cf_fast_success.png')
    elif 'human' in body.lower() or 'just a moment' in title.lower():
        log("Challenge shown - waiting 60s...")
        for i in range(20):
            time.sleep(3)
            if 'dashboard' in page.title().lower() and 'sign-up' not in page.url:
                log("Challenge passed after wait!")
                page.screenshot(path='/tmp/cf_fast_success.png')
                break
            if i == 19:
                log(f"Still challenged: {page.title()} | {page.inner_text('body')[:100]}")
                page.screenshot(path='/tmp/cf_fast_challenge.png')
    else:
        log("FAILED")
        page.screenshot(path='/tmp/cf_fast_fail.png')
    
    browser.close()