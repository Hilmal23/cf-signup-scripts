#!/usr/bin/env python3
"""CF Signup - intercept ALL requests including API calls"""
from playwright.sync_api import sync_playwright
import time, json

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

email = f"cf{int(time.time())}@hilmal.store"
pw = "CfSignup123!"
log(f"Email: {email}")

all_requests = []
all_responses = []

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
    
    # Capture ALL requests
    def on_request(request):
        all_requests.append({
            'url': request.url,
            'method': request.method,
            'post_data': request.post_data,
            'headers': {k: v for k, v in request.headers.items() if k.lower() in ['content-type', 'authorization', 'x-csrf', 'x-requested-with']}
        })
        if request.method == 'POST' or 'api' in request.url.lower():
            log(f">>> POST/API: {request.method} {request.url}")
            if request.post_data:
                log(f"    Data: {request.post_data[:200]}")
    
    def on_response(response):
        status = response.status
        all_responses.append({'url': response.url, 'status': status})
        if status >= 400 or 'api' in response.url.lower():
            log(f"<<< RESP: {status} {response.url}")
    
    page.on("request", on_request)
    page.on("response", on_response)
    
    page.goto("https://dash.cloudflare.com/sign-up", timeout=90000)
    time.sleep(8)
    
    log(f"Title: {page.title()}")
    log(f"URL: {page.url}")
    
    body = page.evaluate("() => document.body ? document.body.innerText.substring(0,300) : ''")
    
    if "email" in body.lower() and "password" in body.lower():
        log("Signup form loaded! Filling...")
        
        # Fill form
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
        
        # Capture requests AFTER fill (before submit)
        before_count = len(all_requests)
        log("Submitting...")
        page.click('button[type="submit"]')
        
        # Wait and capture
        time.sleep(10)
        
        log(f"After - Title: {page.title()}")
        log(f"After - URL: {page.url}")
        body2 = page.evaluate("() => document.body ? document.body.innerText.substring(0,300) : ''")
        log(f"After body: {body2[:200]}")
        
        # Show new requests (after submit)
        log(f"\n=== ALL REQUESTS (total: {len(all_requests)}) ===")
        for r in all_requests:
            if r['method'] == 'POST':
                log(f"POST: {r['url']}")
                log(f"  Data: {r['post_data']}")
                log(f"  Headers: {r['headers']}")
        
        log(f"\n=== RESPONSES with errors ===")
        for r in all_responses:
            if r['status'] >= 400:
                log(f"ERROR {r['status']}: {r['url']}")
        
        if "dashboard" in page.title().lower():
            log("SUCCESS!")
        else:
            page.screenshot(path='/tmp/cf_result.png')
    else:
        log(f"Challenge: {body[:100]}")
    
    browser.close()

log("=== Done ===")