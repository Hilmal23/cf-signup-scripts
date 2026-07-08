#!/usr/bin/env python3
"""CF Signup - intercept exact network request on submit"""
from playwright.sync_api import sync_playwright
import time, json

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

captured = {'request': None, 'response': None}

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
        proxy={
            "server": "http://brd.superproxy.io:33335",
            "username": "brd-customer-hl_c0f6789c-zone-web_unlocker1",
            "password": "ds3ovbwhs69y"
        },
    )
    page = ctx.new_page()
    
    def on_request(request):
        if any(x in request.url for x in ['sign-up', 'signup', 'register', 'account', 'auth', 'user']):
            captured['request'] = {
                'url': request.url,
                'method': request.method,
                'headers': dict(request.headers),
                'post_data': request.post_data,
            }
            log(f"REQUEST: {request.method} {request.url}")
    
    def on_response(response):
        if any(x in response.url for x in ['sign-up', 'signup', 'register', 'account', 'auth', 'user']):
            captured['response'] = {
                'url': response.url,
                'status': response.status,
            }
            log(f"RESPONSE: {response.status} {response.url}")
    
    page.on("request", on_request)
    page.on("response", on_response)
    
    page.goto("https://dash.cloudflare.com/sign-up", timeout=90000)
    time.sleep(6)
    
    log(f"Title: {page.title()}")
    log(f"URL: {page.url}")
    
    body = page.evaluate("() => document.body ? document.body.innerText.substring(0,300) : ''")
    log(f"Body: {body[:200]}")
    
    if "email" in body.lower() and "password" in body.lower():
        log("Filling form...")
        
        # Extract all hidden inputs
        hidden = page.evaluate("""() => {
            const h = {};
            document.querySelectorAll('input[type=hidden]').forEach(el => {
                h[el.name || el.id] = el.value;
            });
            return h;
        }""")
        log(f"Hidden inputs: {hidden}")
        
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
        log("Submitting...")
        page.click('button[type="submit"]')
        time.sleep(10)
        
        log(f"After - Title: {page.title()}")
        log(f"After - URL: {page.url}")
        body2 = page.evaluate("() => document.body ? document.body.innerText.substring(0,500) : ''")
        log(f"After body: {body2}")
        
        if captured['request']:
            log(f"Request URL: {captured['request']['url']}")
            log(f"Method: {captured['request']['method']}")
            log(f"Post data: {str(captured['request']['post_data'])[:300]}")
        if captured['response']:
            log(f"Response status: {captured['response']['status']}")
        
        if "dashboard" in page.title().lower():
            log("SUCCESS!")
        else:
            page.screenshot(path='/tmp/cf_result.png')
    else:
        log(f"Challenge: {body[:100]}")
    
    browser.close()

log("=== Done ===")