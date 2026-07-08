#!/usr/bin/env python3
"""CF Signup - intercept Turnstile token generation"""
from playwright.sync_api import sync_playwright
import time, json

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
    
    # Get cookies
    cookies = ctx.cookies()
    cookie_dict = {c['name']: c['value'] for c in cookies}
    log(f"cf_clearance: {cookie_dict.get('cf_clearance', 'NONE')[:30]}...")
    
    # Fill form
    page.fill('input[name="email"]', email)
    page.fill('input[name="password"]', pw)
    
    # Intercept ALL requests during submit
    all_requests = []
    all_responses = []
    
    def on_request(request):
        all_requests.append({
            'url': request.url,
            'method': request.method,
            'body': request.post_data,
            'headers': dict(request.headers)
        })
    
    def on_response(response):
        all_responses.append({
            'url': response.url,
            'status': response.status
        })
    
    page.on("request", on_request)
    page.on("response", on_response)
    
    log("Submitting...")
    page.click('button[type="submit"]')
    time.sleep(8)
    
    # Find the exact create API request
    create_api = None
    for r in all_requests:
        if '/api/v4/user/create' in r['url']:
            create_api = r
            break
    
    if create_api:
        log(f"\n=== CREATE API REQUEST ===")
        try:
            body = json.loads(create_api['body'])
            log(f"cf_challenge_response: {body.get('cf_challenge_response', 'EMPTY')[:50] if body.get('cf_challenge_response') else 'EMPTY STRING'}")
            log(f"hCaptchaDisplayed: {body.get('hCaptchaDisplayed')}")
            log(f"Full body: {json.dumps(body, indent=2)}")
        except:
            log(f"Body: {create_api['body'][:300]}")
    
    # Check response
    for r in all_responses:
        if 'user/create' in r['url']:
            log(f"\nCREATE RESPONSE: {r['status']}")
    
    # Check for any challenge token response
    log("\n=== All challenge/turnstile responses ===")
    for r in all_responses:
        if 'challenge' in r['url'] or 'turnstile' in r['url'] or 'captcha' in r['url']:
            log(f"  {r['status']}: {r['url']}")
    
    # Check for cf_challenge_response in any request
    log("\n=== All requests with challenge_response ===")
    for r in all_requests:
        if r['body'] and 'challenge_response' in r['body']:
            log(f"  {r['method']}: {r['url']}")
            try:
                body = json.loads(r['body'])
                log(f"  cf_challenge_response: {body.get('cf_challenge_response', 'EMPTY')[:100]}")
            except:
                pass
    
    browser.close()

log("=== Done ===")