#!/usr/bin/env python3
"""CF Signup - REPLICATE the exact API call discovered"""
from playwright.sync_api import sync_playwright
import requests, time, re, json

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
        proxy={"server": "http://brd.superproxy.io:33335", "username": "brd-customer-hl_c0f6789c-zone-web_unlocker1", "password": "ds3ovbwhs69y"},
    )
    page = ctx.new_page()
    
    log("Loading page via BD...")
    page.goto("https://dash.cloudflare.com/sign-up", timeout=90000)
    time.sleep(8)
    
    title = page.title()
    log(f"Title: {title}")
    
    # Get cookies
    cookies = ctx.cookies()
    cookie_dict = {c['name']: c['value'] for c in cookies}
    log(f"cf_clearance: {cookie_dict.get('cf_clearance', 'NONE')[:30]}...")
    log(f"cf_v: {cookie_dict.get('cf_v', 'NONE')}")
    
    # Extract security_token from page
    sec_token = page.evaluate("() => document.querySelector('input[name=\"security_token\"]')?.value || ''")
    log(f"security_token: {sec_token[:40]}...")
    
    # Fill form
    page.fill('input[name="email"]', email)
    page.fill('input[name="password"]', pw)
    time.sleep(0.5)
    
    # Now intercept the exact API call
    captured_create = [None]
    
    def on_request(request):
        if '/api/v4/user/create' in request.url and request.method == 'POST':
            captured_create[0] = {
                'url': request.url,
                'headers': dict(request.headers),
                'body': request.post_data
            }
            log(f"INTERCEPTED create API!")
    
    page.on("request", on_request)
    
    # Click submit to get the fresh legal_stamp and capture the request
    page.click('button[type="submit"]')
    time.sleep(2)  # Wait for request to fire
    
    if captured_create[0]:
        log("Got API call!")
        api_req = captured_create[0]
        
        # Now replicate EXACTLY with Python requests
        log("\n=== REPLICATING API CALL ===")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://dash.cloudflare.com/sign-up',
            'Origin': 'https://dash.cloudflare.com',
        }
        
        rs = requests.Session()
        for name, value in cookie_dict.items():
            rs.cookies.set(name, value, domain='.cloudflare.com', path='/')
        
        log(f"POST to {api_req['url']}")
        
        r = rs.post(
            api_req['url'],
            data=api_req['body'],
            headers={**headers, 'content-type': api_req['headers'].get('content-type', 'application/json')},
            timeout=20
        )
        
        log(f"Status: {r.status_code}")
        log(f"Response: {r.text[:500]}")
        
        if r.status_code == 200:
            log("SUCCESS! Account created!")
        elif r.status_code == 400:
            # Parse error
            try:
                err = r.json()
                log(f"Error: {json.dumps(err, indent=2)}")
            except:
                log(f"Error body: {r.text[:300]}")
    else:
        log("Could not capture create API!")
    
    browser.close()

log("=== Done ===")