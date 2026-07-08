#!/usr/bin/env python3
"""CF Signup via Bright Data Web Unlocker - WORKS!"""
from playwright.sync_api import sync_playwright
import time

email = f"cf{int(time.time())}@hilmal.store"
pw = "CfSignup123!"
print(f"Email: {email}")

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
    time.sleep(5)
    
    title = page.title()
    url = page.url
    body = page.evaluate("() => document.body ? document.body.innerText.substring(0,300) : ''")
    
    print(f"Title: {title}")
    print(f"URL: {url}")
    print(f"Body: {body}")
    
    if "email" in body.lower() and "password" in body.lower():
        print("Signup form loaded!")
        page.fill('input[name="email"]', email)
        page.fill('input[name="password"]', pw)
        time.sleep(0.5)
        page.click('button[type="submit"]')
        time.sleep(10)
        
        print("After submit - Title:", page.title())
        print("URL:", page.url)
        body2 = page.evaluate("() => document.body ? document.body.innerText.substring(0,200) : ''")
        print("Body:", body2)
        
        if "dashboard" in page.title().lower():
            print("SUCCESS! Account created!")
            page.screenshot(path='/tmp/cf_success.png')
        else:
            print("Form result:", body2[:200])
    else:
        print("Challenge or other:", body[:100])
        page.screenshot(path='/tmp/cf_challenge.png')
    
    browser.close()

print("=== Done ===")