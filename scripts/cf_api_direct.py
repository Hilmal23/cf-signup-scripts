#!/usr/bin/env python3
"""CF Signup - intercept exact API call"""
from playwright.sync_api import sync_playwright
import time, json

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

email = f"cf{int(time.time())}@hilmal.store"
pw = "CfSignup123!"
log(f"Email: {email}")

# Capture all network traffic
all_traffic = []

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
        proxy={"server": "http://brd.superproxy.io:33335", "username": "brd-customer-hl_c0f6789c-zone-web_unlocker1", "password": "ds3ovbwhs69y"},
    )
    page = ctx.new_page()
    
    captured_request = [None]  # mutable container
    captured_response = [None]
    
    def on_request(request):
        if 'signup' in request.url.lower() or 'register' in request.url.lower() or request.method == 'POST':
            log(f"> REQUEST: {request.method} {request.url}")
            log(f"  Headers: {json.dumps({k:v for k,v in request.headers.items() if k in ['content-type','x-csrf','authorization','origin','referer']})}")
            if request.post_data:
                log(f"  Body: {request.post_data[:500]}")
            captured_request[0] = {'url': request.url, 'method': request.method, 'headers': dict(request.headers), 'body': request.post_data}
    
    def on_response(response):
        if 'signup' in response.url.lower() or response.status >= 400:
            log(f"< RESPONSE: {response.status} {response.url}")
            captured_response[0] = {'url': response.url, 'status': response.status}
    
    page.on("request", on_request)
    page.on("response", on_response)
    
    log("Loading page via BD...")
    page.goto("https://dash.cloudflare.com/sign-up", timeout=90000)
    time.sleep(8)
    
    log(f"Title: {page.title()}")
    
    # Get cookies
    cookies = ctx.cookies()
    cookie_str = '; '.join([f"{c['name']}={c['value']}" for c in cookies])
    log(f"Cookies: {cookie_str[:200]}")
    
    # Extract hidden values
    sec_token = page.evaluate("() => document.querySelector('input[name=\"security_token\"]')?.value || ''")
    log(f"Security token: {sec_token}")
    
    # Fill form
    page.fill('input[name="email"]', email)
    page.fill('input[name="password"]', pw)
    
    captured_request[0] = None
    log("Submitting...")
    page.click('button[type="submit"]')
    time.sleep(8)
    
    log(f"After - Title: {page.title()}")
    log(f"After - URL: {page.url}")
    
    if captured_request[0]:
        req = captured_request[0]
        log(f"\n=== CAPTURED REQUEST ===")
        log(f"URL: {req['url']}")
        log(f"Method: {req['method']}")
        log(f"Body: {req['body']}")
        # Save for API call
        with open('/tmp/cf_captured_req.json', 'w') as f:
            json.dump(req, f, indent=2)
        log("Saved to /tmp/cf_captured_req.json")
    else:
        log("No signup POST request captured!")
    
    if captured_response[0]:
        log(f"Response: {captured_response[0]}")
    
    browser.close()

log("=== Done ===")