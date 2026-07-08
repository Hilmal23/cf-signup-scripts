#!/usr/bin/env python3
"""CF signup - check actual page content"""
from playwright.sync_api import sync_playwright
import time

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

BRD_PROXY = {
    'server': 'http://brd.superproxy.io:33335',
    'username': 'brd-customer-hl_c0f6789c-zone-web_unlocker1',
    'password': 'ds3ovbwhs69y'
}

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        executable_path='/usr/bin/chromium-browser',
        args=['--no-sandbox', '--disable-setuid-sandbox', '--ignore-certificate-errors', '--allow-running-insecure-content']
    )
    ctx = browser.new_context(proxy=BRD_PROXY, ignore_https_errors=True)
    page = ctx.new_page()
    
    page.goto("https://dash.cloudflare.com/sign-up", timeout=60000)
    time.sleep(8)  # Wait longer for JS
    
    title = page.title()
    url = page.url
    
    log(f"Title: {title}")
    log(f"URL: {url}")
    
    # Try evaluating different parts of the DOM
    body_len = page.evaluate("() => document.body ? document.body.innerHTML.length : 0")
    html_len = page.evaluate("() => document.documentElement ? document.documentElement.innerHTML.length : 0")
    body_text = page.evaluate("() => { try { return document.body ? document.body.innerText : ''; } catch(e) { return 'ERROR: ' + e.message; } }")
    
    log(f"Body HTML length: {body_len}")
    log(f"Document HTML length: {html_len}")
    log(f"Body text: '{body_text[:200]}'")
    
    # Check for specific classes
    login_form = page.query_selector('form[action*="sign-up"]')
    signup_btn = page.query_selector('button[type="submit"]')
    
    log(f"Sign-up form: {login_form is not None}")
    log(f"Submit button: {signup_btn is not None}")
    
    # Take screenshot
    page.screenshot(path='/tmp/cf_chrome_check.png', full_page=True)
    log("Screenshot saved!")
    
    # Wait more
    time.sleep(10)
    
    title2 = page.title()
    body_text2 = page.evaluate("() => { try { return document.body ? document.body.innerText : ''; } catch(e) { return 'ERR'; } }")
    log(f"After 18s wait - Title: {title2}")
    log(f"After 18s wait - Body: '{body_text2[:200]}'")
    
    page.screenshot(path='/tmp/cf_chrome_check2.png', full_page=True)
    browser.close()

log("=== Done ===")