#!/usr/bin/env python3
"""CF Signup - intercept challenge platform and get response token"""
from playwright.sync_api import sync_playwright
import requests, time, json, re

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

email = f"cf{int(time.time())}@hilmal.store"
pw = "CfSignup123!"
log(f"Email: {email}")

BRD = 'http://brd-customer-hl_c0f6789c-zone-web_unlocker1:ds3ovbwhs69y@brd.superproxy.io:33335'

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        executable_path="/snap/chromium/current/usr/lib/chromium-browser/chrome",
        args=[
            "--no-sandbox", "--disable-setuid-sandbox",
            "--ignore-certificate-errors",
            "--allow-running-insecure-content",
            "--ignore-certificate-errors-spki-list=*",
        ]
    )
    ctx = browser.new_context(
        proxy={"server": "http://brd.superproxy.io:33335", "username": "brd-customer-hl_c0f6789c-zone-web_unlocker1", "password": "ds3ovbwhs69y"},
    )
    page = ctx.new_page()
    
    log("Loading page via BD...")
    page.goto("https://dash.cloudflare.com/sign-up", timeout=90000)
    time.sleep(8)
    
    # Get all cookies
    cookies = ctx.cookies()
    cookie_dict = {c['name']: c['value'] for c in cookies}
    log(f"Cookies: {list(cookie_dict.keys())}")
    log(f"cf_clearance: {cookie_dict.get('cf_clearance', 'NONE')[:30]}...")
    
    # Fill form
    page.fill('input[name="email"]', email)
    page.fill('input[name="password"]', pw)
    
    # Capture ALL requests and responses
    all_traffic = []
    
    def on_request(request):
        all_traffic.append({'type': 'req', 'url': request.url, 'method': request.method, 'body': request.post_data})
    
    def on_response(response):
        all_traffic.append({'type': 'res', 'url': response.url, 'status': response.status})
    
    page.on("request", on_request)
    page.on("response", on_response)
    
    log("Submitting...")
    page.click('button[type="submit"]')
    time.sleep(10)
    
    log(f"After - Title: {page.title()}")
    log(f"After - URL: {page.url}")
    
    # Show all traffic
    log(f"\n=== ALL TRAFFIC ({len(all_traffic)} items) ===")
    for t in all_traffic:
        if t['type'] == 'req':
            if 'challenge' in t['url'] or 'api' in t['url'].lower() or t['method'] == 'POST':
                log(f">> {t['method']} {t['url']}")
                if t['body']:
                    log(f"   Body: {t['body'][:200]}")
        else:
            if t['status'] >= 400 or 'challenge' in t['url'] or 'turnstile' in t['url']:
                log(f"<< {t['status']} {t['url']}")
    
    # Check for create API response
    for t in all_traffic:
        if t['type'] == 'res' and 'user/create' in t['url']:
            log(f"\nCREATE API response status: {t['status']}")
        if t['type'] == 'res' and 'turnstile' in t['url']:
            log(f"TURNSTILE response: {t['url']} -> {t['status']}")
        if t['type'] == 'res' and 'challenge' in t['url']:
            log(f"CHALLENGE response: {t['url']} -> {t['status']}")
    
    browser.close()

log("=== Done ===")