#!/usr/bin/env python3
"""CF Signup - Python API call through BD proxy"""
from playwright.sync_api import sync_playwright
import requests, time, json

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
    
    cookies = ctx.cookies()
    cookie_dict = {c['name']: c['value'] for c in cookies}
    log(f"cf_clearance: {cookie_dict.get('cf_clearance', 'NONE')[:30]}...")
    
    sec_token = page.evaluate("() => document.querySelector('input[name=\"security_token\"]')?.value || ''")
    log(f"security_token: {sec_token[:40]}...")
    
    # Fill form + capture exact request
    page.fill('input[name="email"]', email)
    page.fill('input[name="password"]', pw)
    
    captured = [None]
    def on_request(request):
        if '/api/v4/user/create' in request.url:
            captured[0] = request.post_data
    
    page.on("request", on_request)
    page.click('button[type="submit"]')
    time.sleep(3)
    
    if not captured[0]:
        log("No create API captured!")
        browser.close()
        exit(1)
    
    log("Got create API data!")
    api_body = captured[0]
    log(f"Body: {api_body[:200]}")
    
    # Replicate with Python requests through BD proxy
    log("\n=== Python API through BD proxy ===")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://dash.cloudflare.com/sign-up',
        'Origin': 'https://dash.cloudflare.com',
        'content-type': 'application/json',
    }
    
    rs = requests.Session()
    rs.proxies = {'http': BRD, 'https': BRD}
    rs.verify = False
    
    for name, value in cookie_dict.items():
        rs.cookies.set(name, value, domain='.cloudflare.com', path='/')
    
    r = rs.post('https://dash.cloudflare.com/api/v4/user/create', data=api_body, headers=headers, timeout=20)
    log(f"Status: {r.status_code}")
    log(f"Response: {r.text[:500]}")
    
    if r.status_code == 200:
        log("SUCCESS! Account created!")
    elif r.status_code == 400:
        try:
            err = r.json()
            log(f"Error: {json.dumps(err, indent=2)}")
        except:
            log(f"Error: {r.text[:300]}")
    
    browser.close()

log("=== Done ===")