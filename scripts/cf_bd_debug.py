#!/usr/bin/env python3
"""CF Signup debug"""
from playwright.sync_api import sync_playwright
import time

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
    
    page.goto("https://dash.cloudflare.com/sign-up", timeout=90000)
    time.sleep(8)
    
    print("Title:", page.title())
    print("URL:", page.url)
    print("HTML length:", len(page.content()))
    
    # Get full innerText
    body_text = page.evaluate("() => document.body ? document.body.innerText : 'NO BODY'")
    print("Body text:", body_text[:300])
    
    # Get all text
    all_text = page.evaluate("() => document.documentElement.innerText.substring(0, 300)")
    print("All text:", all_text[:300])
    
    # Check for iframe content
    iframes = page.query_selector_all("iframe")
    print(f"Iframes: {len(iframes)}")
    for i, f in enumerate(iframes):
        src = f.get_attribute("src")
        print(f"  iframe {i}: {src}")
    
    # Check for specific elements
    email_input = page.query_selector('input[name="email"]')
    challenge = page.query_selector('[data-testid="challenge"]')
    cf_challenge = page.query_selector('#cf-challenge-container')
    
    print(f"Email input: {email_input is not None}")
    print(f"Challenge element: {challenge is not None}")
    print(f"CF challenge container: {cf_challenge is not None}")
    
    page.screenshot(path='/tmp/cf_debug.png', full_page=True)
    print("Screenshot saved!")
    
    browser.close()

print("=== Done ===")