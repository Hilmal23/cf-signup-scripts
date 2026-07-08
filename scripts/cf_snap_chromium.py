#!/usr/bin/env python3
"""CF signup - Snap Chromium + Bright Data proxy"""
from playwright.sync_api import sync_playwright
import time

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

BRD_PROXY = {
    'server': 'http://brd.superproxy.io:33335',
    'username': 'brd-customer-hl_c0f6789c-zone-web_unlocker1',
    'password': 'ds3ovbwhs69y'
}

email = f"snapcf{int(time.time())}@hilmal.store"
pw = "Snapcf123!"
log(f"Email: {email}")

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        executable_path='/snap/chromium/current/usr/lib/chromium-browser/chrome',
        args=[
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--ignore-certificate-errors',
            '--allow-running-insecure-content',
            '--disable-gpu',
        ]
    )
    ctx = browser.new_context(
        proxy=BRD_PROXY,
        ignore_https_errors=True,
    )
    page = ctx.new_page()
    
    log("Navigating to CF signup...")
    page.goto("https://dash.cloudflare.com/sign-up", timeout=90000)
    time.sleep(6)
    
    title = page.title()
    url = page.url
    body_text = page.evaluate("() => document.body ? document.body.innerText.substring(0, 300) : ''")
    
    log(f"Title: {title}")
    log(f"URL: {url}")
    log(f"Body: {body_text}")
    
    if 'dashboard' in title.lower() and 'sign-up' not in url:
        log("SUCCESS! Logged in!")
        page.screenshot(path='/tmp/cf_snap_success.png')
    elif 'email' in body_text.lower() and 'password' in body_text.lower():
        if 'let us know' in body_text.lower():
            log("Challenge shown")
            page.screenshot(path='/tmp/cf_snap_challenge.png')
        else:
            log("Signup form loaded! NO CHALLENGE!")
            page.screenshot(path='/tmp/cf_snap_form.png')
            
            page.fill('input[name="email"]', email)
            page.fill('input[name="password"]', pw)
            time.sleep(0.5)
            page.click('button[type="submit"]')
            log("Clicked submit!")
            time.sleep(10)
            
            if 'dashboard' in page.title().lower():
                log("SUCCESS! Account created!")
                page.screenshot(path='/tmp/cf_snap_account.png')
            else:
                body2 = page.evaluate("() => document.body ? document.body.innerText.substring(0, 200) : ''")
                log(f"Result: {body2}")
    else:
        log("Other result")
        page.screenshot(path='/tmp/cf_snap_other.png')
    
    browser.close()

log("=== Done ===")