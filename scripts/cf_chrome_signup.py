#!/usr/bin/env python3
"""CF signup via Chromium + Bright Data proxy"""
from playwright.sync_api import sync_playwright
import time

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

BRD_PROXY = {
    'server': 'http://brd.superproxy.io:33335',
    'username': 'brd-customer-hl_c0f6789c-zone-web_unlocker1',
    'password': 'ds3ovbwhs69y'
}

email = f"chrometest{int(time.time())}@hilmal.store"
pw = "ChromeTest123!"
log(f"Email: {email}")

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        executable_path='/usr/bin/chromium-browser',
        args=[
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--ignore-certificate-errors',
            '--allow-running-insecure-content',
            '--disable-web-security',
        ]
    )
    ctx = browser.new_context(
        proxy=BRD_PROXY,
        ignore_https_errors=True,
    )
    page = ctx.new_page()
    
    page.goto("https://dash.cloudflare.com/sign-up", timeout=60000)
    time.sleep(5)
    
    title = page.title()
    url = page.url
    body = page.inner_text('body')
    
    log(f"Page: {title} | {url}")
    log(f"Body: {body[:200]}")
    
    if 'dashboard' in title.lower() and 'sign-up' not in url:
        log("SUCCESS! Logged in!")
    elif 'email' in body.lower() and 'password' in body.lower():
        log("Signup form loaded!")
        page.fill('input[name="email"]', email)
        page.fill('input[name="password"]', pw)
        time.sleep(0.5)
        page.click('button[type="submit"]')
        log("Submitted!")
        time.sleep(10)
        
        if 'dashboard' in page.title().lower():
            log("SUCCESS! Account created!")
            page.screenshot(path='/tmp/cf_chrome_success.png')
        else:
            log(f"Result: {page.inner_text('body')[:200]}")
    else:
        log("Challenge or other")
        page.screenshot(path='/tmp/cf_chrome_result.png')
    
    browser.close()

log("=== Done ===")