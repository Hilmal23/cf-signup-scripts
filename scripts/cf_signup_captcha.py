#!/usr/bin/env python3
"""CF signup - clear storage + solve CAPTCHA"""
from camoufox import Camoufox
import time, re

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def solve_captcha(page):
    """Try to solve by checking/unchecking challenge"""
    # Method 1: Click the challenge iframe and interact
    iframe = page.query_selector('iframe[src*="turnstile"]')
    if iframe:
        log("Turnstile iframe found!")
        # Try clicking
        try:
            iframe.click()
            time.sleep(3)
            log(f"After iframe click: {page.title()}")
        except:
            pass
    
    # Method 2: Wait for auto-solve
    log("Waiting for challenge to resolve...")
    for i in range(30):
        time.sleep(2)
        title = page.title()
        body = page.inner_text('body')
        log(f"[{i*2}s] {title[:50]}")
        if "Just a moment" not in title and "human" not in body.lower():
            log(f"Challenge passed!")
            return True
        if i > 10 and "unable to sign up" in body.lower():
            log("Permanently blocked")
            return False
    return False

email = f"test{int(time.time())}@hilmal.store"
pw = "TestPass123!"
log(f"Email: {email}")

with Camoufox(headless=True, geoip=False) as browser:
    ctx = browser.new_context()
    # Clear ALL storage
    ctx.clear_cookies()
    
    page = ctx.new_page()
    page.goto("https://dash.cloudflare.com/sign-up", timeout=45000)
    time.sleep(8)
    log(f"Initial: {page.title()}")
    
    # Fill form
    page.fill('input[name="email"]', email)
    time.sleep(0.5)
    page.fill('input[name="password"]', pw)
    time.sleep(1)
    
    # Check for CAPTCHA before submit
    if "human" in page.inner_text('body').lower():
        log("CAPTCHA pre-submit detected")
        if not solve_captcha(page):
            log("Captcha solve failed")
            ctx.close()
            browser.close()
            exit(1)
    
    # Submit
    page.click('button[type="submit"]')
    time.sleep(5)
    
    # Check after submit
    title = page.title()
    body = page.inner_text('body')
    log(f"After submit: {title}")
    
    if "human" in body or "Just a moment" in title:
        log("CAPTCHA challenge showing")
        solve_captcha(page)
    
    log(f"Final URL: {page.url}")
    log(f"Final title: {title}")
    
    page.screenshot(path='/tmp/cf_final.png')
    log("Screenshot!")
    
    browser.close()