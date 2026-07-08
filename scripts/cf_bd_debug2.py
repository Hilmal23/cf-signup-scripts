#!/usr/bin/env python3
"""CF Signup - debug what happens on submit"""
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
        executable_path="/snap/chromium/current/usr/lib/chromium-browser/chrome",
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
    )
    page = ctx.new_page()
    
    # Console errors
    errors = []
    def on_console(msg):
        if msg.type == 'error':
            errors.append(msg.text)
            log(f"CONSOLE ERROR: {msg.text[:100]}")
    
    page.on("console", on_console)
    
    page.goto("https://dash.cloudflare.com/sign-up", timeout=90000)
    
    # Wait for network idle
    page.wait_for_load_state("networkidle", timeout=30000)
    time.sleep(3)
    
    log(f"Title: {page.title()}")
    log(f"URL: {page.url}")
    
    # Check for signup form
    email_input = page.query_selector('input[name="email"]')
    pw_input = page.query_selector('input[name="password"]')
    submit_btn = page.query_selector('button[type="submit"]')
    
    log(f"Email input found: {email_input is not None}")
    log(f"PW input found: {pw_input is not None}")
    log(f"Submit btn found: {submit_btn is not None}")
    
    if email_input:
        email_input.fill(email)
        log("Email filled!")
    if pw_input:
        pw_input.fill(pw)
        log("Password filled!")
    
    # Screenshot before submit
    page.screenshot(path='/tmp/cf_before.png')
    log("Screenshot before submit saved")
    
    # Try JS click instead
    log("Clicking submit via JS...")
    page.evaluate("""() => {
        const btn = document.querySelector('button[type="submit"]');
        if (btn) {
            log('Found submit btn: ' + btn.disabled);
            btn.click();
            log('Clicked!');
        } else {
            log('No submit btn!');
        }
    }""")
    
    # Alternative: press Enter
    log("Pressing Enter on password field...")
    if pw_input:
        pw_input.press("Enter")
    
    time.sleep(8)
    
    log(f"After - Title: {page.title()}")
    log(f"After - URL: {page.url}")
    
    body = page.evaluate("() => document.body ? document.body.innerText.substring(0,300) : ''")
    log(f"After body: {body}")
    
    page.screenshot(path='/tmp/cf_after.png')
    log("Screenshot after submit saved")
    
    if errors:
        log(f"Console errors: {errors}")
    else:
        log("No console errors!")
    
    browser.close()

log("=== Done ===")