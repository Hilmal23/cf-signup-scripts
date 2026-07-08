#!/usr/bin/env python3
"""CF Signup - exact request replication with all headers"""
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
    
    page.fill('input[name="email"]', email)
    page.fill('input[name="password"]', pw)
    
    # Capture exact request headers
    captured = [None]
    def on_request(request):
        if '/api/v4/user/create' in request.url and request.method == 'POST':
            captured[0] = {
                'url': request.url,
                'headers': dict(request.headers),
                'body': request.post_data
            }
            log(f"Captured create API!")
    
    page.on("request", on_request)
    page.click('button[type="submit"]')
    time.sleep(5)
    
    if not captured[0]:
        log("No capture!")
        browser.close()
        exit(1)
    
    req = captured[0]
    log(f"\n=== Exact request headers ===")
    for k, v in req['headers'].items():
        log(f"  {k}: {v}")
    
    # Python API call with EXACT headers
    log("\n=== Python API with exact headers ===")
    
    rs = requests.Session()
    rs.proxies = {'http': BRD, 'https': BRD}
    rs.verify = False
    
    for name, value in cookie_dict.items():
        rs.cookies.set(name, value, domain='.cloudflare.com', path='/')
    
    r = rs.post(
        req['url'],
        data=req['body'],
        headers=req['headers'],
        timeout=30
    )
    
    log(f"Status: {r.status_code}")
    log(f"Response: {r.text[:500]}")
    
    if r.status_code == 200:
        log("SUCCESS! Account created!")
        page.screenshot(path='/tmp/cf_success.png')
    elif r.status_code == 400:
        try:
            err = r.json()
            log(f"Error: {json.dumps(err, indent=2)}")
        except:
            log(f"Error: {r.text[:300]}")
    else:
        log(f"Other status: {r.status_code}")
        log(f"Response: {r.text[:300]}")
    
    browser.close()

log("=== Done ===")