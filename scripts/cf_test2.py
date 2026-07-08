#!/usr/bin/env python3
"""CF Signup - direct wait for email input"""
from playwright.sync_api import sync_playwright
import time

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

email = f"cf{int(time.time())}@hilmal.store"
pw = "CfSignup123!"
log(f"Email: {email}")

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--ignore-certificate-errors",
            "--allow-running-insecure-content",
            "--ignore-certificate-errors-spki-list=*",
        ]
    )
    ctx = browser.new_context(
        proxy={
            "server": "http://brd.superproxy.io:33335",
            "username": "brd-customer-hl_c0f6789c-zone-web_unlocker1",
            "password": "ds3ovbwhs69y"
        },
        viewport={"width": 1920, "height": 1080},
    )
    page = ctx.new_page()
    
    errors = []
    def on_console(msg):
        if msg.type == 'error':
            errors.append(msg.text)
            log(f"ERR: {msg.text[:80]}")
    
    page.on("console", on_console)
    
    log("Navigating to CF signup...")
    page.goto("https://dash.cloudflare.com/sign-up", timeout=60000)
    time.sleep(5)
    
    log(f"Title: {page.title()}")
    log(f"URL: {page.url}")
    
    # Wait for email input specifically
    try:
        email_input = page.wait_for_selector('input[name="email"]', timeout=20000)
        log("Email input found!")
        page.screenshot(path='/tmp/cf_form.png')
        log("Screenshot saved")
    except:
        log("Email input NOT found!")
        page.screenshot(path='/tmp/cf_noform.png')
        body = page.evaluate("() => document.body ? document.body.innerText.substring(0,300) : ''")
        log(f"Body: {body}")
        browser.close()
        exit(1)
    
    # Check for turnstile challenge overlay
    turnstile = page.query_selector('.cf-turnstile, [data-testid="challenge"]')
    log(f"Turnstile present: {turnstile is not None}")
    
    log("Filling form...")
    page.fill('input[name="email"]', email)
    time.sleep(0.3)
    page.fill('input[name="password"]', pw)
    time.sleep(0.5)
    
    page.screenshot(path='/tmp/cf_filled.png')
    log("Form filled! Screenshot saved")
    
    # Click submit
    page.click('button[type="submit"]')
    log("Clicked submit!")
    
    # Wait for response
    time.sleep(10)
    
    log(f"After - Title: {page.title()}")
    log(f"After - URL: {page.url}")
    body = page.evaluate("() => document.body ? document.body.innerText.substring(0,400) : ''")
    log(f"After body: {body}")
    page.screenshot(path='/tmp/cf_after.png')
    
    if errors:
        log(f"Errors during run: {len(errors)}")
    else:
        log("No console errors!")
    
    browser.close()

log("=== Done ===")