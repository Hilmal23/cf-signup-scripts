#!/usr/bin/env python3
"""CF Signup full test"""
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
    time.sleep(6)
    
    print(f"Title: {page.title()}")
    print(f"URL: {page.url}")
    
    body = page.evaluate("() => document.body ? document.body.innerText.substring(0,300) : ''")
    print(f"Body: {body}")
    
    if "email" in body.lower() and "password" in body.lower():
        print("Signup form loaded! Filling...")
        
        # Find email input
        email_input = page.query_selector('input[name="email"]')
        pw_input = page.query_selector('input[name="password"]')
        
        if email_input and pw_input:
            email_input.fill(email)
            pw_input.fill(pw)
            print("Form filled!")
        else:
            print("Input selectors not found!")
            # Try generic selectors
            inputs = page.query_selector_all('input[type="email"], input[type="text"]')
            for inp in inputs:
                inp.fill(email)
            pws = page.query_selector_all('input[type="password"]')
            for inp in pws:
                inp.fill(pw)
        
        time.sleep(0.5)
        page.click('button[type="submit"]')
        print("Clicked submit!")
        time.sleep(10)
        
        print("After submit:")
        print(f"Title: {page.title()}")
        print(f"URL: {page.url}")
        body2 = page.evaluate("() => document.body ? document.body.innerText.substring(0,200) : ''")
        print(f"Body: {body2}")
        
        if "dashboard" in page.title().lower():
            print("SUCCESS! Account created!")
        else:
            print("Checking for email verification...")
    else:
        print(f"Challenge or other: {body[:100]}")
        page.screenshot(path='/tmp/cf_challenge.png')
    
    browser.close()

print("=== Done ===")