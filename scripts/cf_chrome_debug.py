#!/usr/bin/env python3
"""CF signup - Chromium debug + screenshot"""
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
            '--disable-features=IsolateOrigins,site-per-process',
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
    
    log(f"Title: {title}")
    log(f"URL: {url}")
    
    # Check body content differently
    html = page.content()
    log(f"HTML length: {len(html)}")
    
    # Check if there's a body
    body_visible = page.evaluate("() => { const b = document.body; return b ? b.innerText.substring(0, 300) : 'NO BODY'; }")
    log(f"Body text: '{body_visible}'")
    
    # Check for specific elements
    signup_form = page.query_selector('input[name="email"]')
    challenge = page.query_selector('[data-testid="challenge"]')
    cf_challenge = page.query_selector('#cf-challenge-container')
    
    log(f"Email input found: {signup_form is not None}")
    log(f"Challenge element found: {challenge is not None}")
    log(f"CF challenge container: {cf_challenge is not None}")
    
    # Screenshot
    page.screenshot(path='/tmp/cf_chrome_debug.png', full_page=True)
    log("Screenshot saved!")
    
    # Try to evaluate page content
    all_text = page.evaluate("() => document.body ? document.body.innerText : document.documentElement.innerText")
    log(f"All text: '{all_text[:300]}'")
    
    browser.close()

log("=== Done ===")