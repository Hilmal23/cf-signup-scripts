#!/usr/bin/env python3
"""CF Signup - browser load page + API submit with cookies"""
from playwright.sync_api import sync_playwright
import requests, time, re, json

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

BRD = 'http://brd-customer-hl_c0f6789c-zone-web_unlocker1:ds3ovbwhs69y@brd.superproxy.io:33335'

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
    
    log("Loading page via BD proxy...")
    page.goto("https://dash.cloudflare.com/sign-up", timeout=90000)
    time.sleep(6)
    
    title = page.title()
    body = page.evaluate("() => document.body ? document.body.innerText.substring(0,200) : ''")
    log(f"Title: {title}")
    log(f"Body: {body[:200]}")
    
    # Extract ALL cookies from browser
    cookies = ctx.cookies()
    cookie_dict = {c['name']: c['value'] for c in cookies}
    log(f"Browser cookies: {list(cookie_dict.keys())}")
    log(f"cf_v: {cookie_dict.get('cf_v', 'NONE')}")
    log(f"__cf_bm: {cookie_dict.get('__cf_bm', 'NONE')[:30]}...")
    
    # Check if form loaded
    if "email" not in body.lower() or "password" not in body.lower():
        log("Signup form NOT loaded!")
        browser.close()
        exit(1)
    
    log("Signup form loaded via browser!")
    
    # Now make API call with browser cookies (NO proxy this time)
    log("\n=== Making API call with browser cookies ===")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Origin': 'https://dash.cloudflare.com',
        'Referer': 'https://dash.cloudflare.com/sign-up',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
    }
    
    # Build session with browser cookies
    rs = requests.Session()
    for name, value in cookie_dict.items():
        rs.cookies.set(name, value, domain='.cloudflare.com', path='/')
    
    # Step 1: GET signup page to get security token
    log("GET signup page...")
    r = rs.get('https://dash.cloudflare.com/sign-up', timeout=20)
    log(f"GET: {r.status_code}, URL: {r.url}")
    
    # Extract CSRF/security tokens from HTML
    security_token = re.search(r'name="security_token"[^>]*value="([^"]+)"', r.text)
    csrf_token = re.search(r'name="_csrf"[^>]*value="([^"]+)"', r.text)
    action_url = re.search(r'<form[^>]*action="([^"]+)"', r.text)
    
    log(f"Security token: {security_token.group(1)[:30] if security_token else 'NONE'}")
    log(f"CSRF token: {csrf_token.group(1)[:30] if csrf_token else 'NONE'}")
    log(f"Form action: {action_url.group(1) if action_url else 'NONE'}")
    
    # Step 2: POST signup form
    form_data = {
        'email': email,
        'password': pw,
        'skip_submission': 'false',
    }
    if security_token:
        form_data['security_token'] = security_token.group(1)
    if csrf_token:
        form_data['_csrf'] = csrf_token.group(1)
    
    log(f"Posting to {action_url.group(1) if action_url else '/api/v4/signup'}")
    log(f"Form data: {json.dumps(form_data)}")
    
    r2 = rs.post(
        action_url.group(1) if action_url else 'https://dash.cloudflare.com/sign-up',
        data=form_data,
        headers={**headers, 'Content-Type': 'application/x-www-form-urlencoded'},
        allow_redirects=True,
        timeout=20
    )
    log(f"POST result: {r2.status_code}")
    log(f"POST URL: {r2.url}")
    log(f"POST body: {r2.text[:300]}")
    
    # Check for email verification
    if 'verify' in r2.text.lower() or 'sent' in r2.text.lower() or r2.status_code in (200, 302):
        log("SUCCESS! Account might be created!")
    else:
        log("API call failed or redirected")
    
    browser.close()

log("=== Done ===")