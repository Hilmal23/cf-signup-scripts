#!/usr/bin/env python3
"""Quick fix: check if token value is truthy (not just key exists)"""
from playwright.sync_api import sync_playwright
import time, json, requests

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

TWOCAPTCHA_KEY = "3da28555894fd89bb569b748731e9400"
SITEKEY = "0x4AAAAAAAJel0iaAR3mgkjp"
PAGE_URL = "https://dash.cloudflare.com/sign-up"
CHROMIUM = "/snap/chromium/current/usr/lib/chromium-browser/chrome"
PROXY = {'server': 'http://brd.superproxy.io:33335', 'username': 'brd-customer-hl_c0f6789c-zone-web_unlocker1', 'password': 'ds3ovbwhs69y'}
CHROME_ARGS = ["--no-sandbox","--disable-setuid-sandbox","--ignore-certificate-errors","--allow-running-insecure-content","--ignore-certificate-errors-spki-list=*"]

def solve():
    log("Solving...")
    r = requests.get(f"http://2captcha.com/in.php?key={TWOCAPTCHA_KEY}&method=turnstile&pageurl={PAGE_URL}&sitekey={SITEKEY}&json=1", timeout=15)
    result = r.json()
    if result.get('status') != 1:
        return None
    job_id = result['request']
    for i in range(40):
        time.sleep(3)
        r2 = requests.get(f"http://2captcha.com/res.php?key={TWOCAPTCHA_KEY}&action=get&id={job_id}&json=1", timeout=10)
        res = r2.json()
        if res.get('status') == 1:
            return res['request']
        if 'CAPCHA_NOT_READY' not in str(res):
            return None
    return None

def signup(token):
    email = f"cf{int(time.time()*1000)}@hilmal.store"
    pw = "CfSignup123!"
    log(f"Email: {email}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=CHROMIUM, args=CHROME_ARGS)
        ctx = browser.new_context(proxy=PROXY)
        page = ctx.new_page()
        
        page.goto(PAGE_URL, timeout=60000)
        time.sleep(10)
        
        for _ in range(5):
            try:
                allow = page.query_selector('button:has-text("Allow All")')
                if allow and allow.is_visible():
                    allow.click()
                    time.sleep(1)
                    break
            except:
                pass
            time.sleep(1)
        
        # Inject token into hidden form field
        page.evaluate(f'''() => {{
            var existing = document.querySelector('input[name="cf_challenge_response"]');
            if (existing) {{
                existing.value = "{token}";
            }} else {{
                var input = document.createElement('input');
                input.type = "hidden";
                input.name = "cf_challenge_response";
                input.value = "{token}";
                var form = document.querySelector('form');
                if (form) form.appendChild(input);
                else document.body.appendChild(input);
            }}
            window.cf_challenge_response = "{token}";
        }}''')
        
        # Wait for cf_clearance
        for i in range(10):
            cookies = {c["name"]: c["value"] for c in ctx.cookies()}
            if 'cf_clearance' in cookies:
                log(f"cf_clearance: {cookies['cf_clearance'][:40]}... (waited {i*2}s)")
                break
            time.sleep(2)
            if i == 9:
                log("No cf_clearance cookie")
        
        # Fill form
        email_inp = page.query_selector('input[name="email"]')
        if not email_inp or not email_inp.is_visible():
            log("No email input!")
            browser.close()
            return
        
        email_inp.fill(email)
        time.sleep(0.3)
        pw_inp = page.query_selector('input[name="password"]')
        pw_inp.fill(pw)
        time.sleep(0.3)
        
        captured_res = [None]
        def on_res(resp):
            if 'user/create' in resp.url:
                captured_res[0] = resp
        page.on("response", on_res)
        
        # Intercept and LOG the request body before it goes out
        captured_req = [None]
        def on_req(req):
            if 'user/create' in req.url:
                captured_req[0] = req
        page.on("request", on_req)
        
        log("Submitting...")
        pw_inp.press('Enter')
        time.sleep(10)
        
        log(f"After: {page.title()} | {page.url}")
        
        if captured_req[0]:
            body = captured_req[0].post_data
            if body:
                try:
                    data = json.loads(body)
                    token_val = data.get('cf_challenge_response', '')
                    # Check if token VALUE is non-empty (not just key exists)
                    log(f"cf_challenge_response value: '{token_val}' (len={len(token_val)})")
                    log(f"Token value first 50 chars: {token_val[:50]}")
                    log(f"Token value matches solved: {token_val.startswith(token[:50])}")
                    log(f"Body has non-empty token: {len(token_val) > 20}")
                except:
                    log(f"Body: {body[:200]}")
        
        if captured_res[0]:
            log(f"API status: {captured_res[0].status}")
            try:
                body = captured_res[0].json()
                if body.get('success'):
                    log("===== SUCCESS! =====")
                else:
                    code = body.get('errors', [{}])[0].get('code')
                    msg = body.get('errors', [{}])[0].get('message')
                    log(f"Error {code}: {msg}")
            except:
                log(f"Response: {captured_res[0].text[:300]}")
        
        page.screenshot(path='/tmp/cf_result.png')
        browser.close()

def main():
    log("=== CF Signup - Token Value Check ===")
    token = solve()
    if token:
        signup(token)
    log("Done")

if __name__ == '__main__':
    main()