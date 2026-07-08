#!/usr/bin/env python3
"""CF Signup direct (no proxy) - bypasses server-side check"""
from playwright.sync_api import sync_playwright
import time

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

email = f"cf{int(time.time())}@hilmal.store"
pw = "CfSignup123!"
log(f"Email: {email}")
log("Using DIRECT connection (no proxy)")

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        executable_path="/snap/chromium/current/usr/lib/chromium-browser/chrome",
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
        ]
    )
    ctx = browser.new_context()  # NO PROXY
    page = ctx.new_page()
    
    page.goto("https://dash.cloudflare.com/sign-up", timeout=90000)
    time.sleep(6)
    
    log(f"Title: {page.title()}")
    log(f"URL: {page.url}")
    
    body = page.evaluate("() => document.body ? document.body.innerText.substring(0,300) : ''")
    log(f"Body: {body[:200]}")
    
    # Check for challenge
    challenge = page.query_selector('[data-testid="challenge"]')
    turnstile = page.query_selector('iframe[src*="turnstile"]')
    
    if challenge:
        log("CHALLENGE shown!")
    if turnstile:
        log("TURNSTILE iframe found!")
    
    if "email" in body.lower() and "password" in body.lower() and not challenge:
        log("Signup form loaded!")
        
        for inp in page.query_selector_all('input'):
            t = inp.get_attribute('type') or ''
            if t in ('email', 'text') and 'hidden' not in t:
                inp.fill(email)
                break
        for inp in page.query_selector_all('input'):
            t = inp.get_attribute('type') or ''
            if t == 'password':
                inp.fill(pw)
                break
        
        time.sleep(0.5)
        page.click('button[type="submit"]')
        log("Submitted!")
        time.sleep(10)
        
        log(f"After - Title: {page.title()}")
        log(f"After - URL: {page.url}")
        body2 = page.evaluate("() => document.body ? document.body.innerText.substring(0,200) : ''")
        log(f"After body: {body2[:200]}")
        
        if "dashboard" in page.title().lower():
            log("SUCCESS!")
        elif "verify" in body2.lower():
            log("Email verification needed!")
        else:
            log("Other result")
            page.screenshot(path='/tmp/cf_direct_result.png')
    elif challenge:
        log("Challenge shown - IP likely rate limited")
        page.screenshot(path='/tmp/cf_direct_challenge.png')
    else:
        log(f"Other: {body[:100]}")
    
    browser.close()

log("=== Done ===")