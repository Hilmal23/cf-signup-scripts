#!/usr/bin/env python3
"""
CF Signup - SIMPLE: Solve once → cf_clearance cookie → submit browser form
Key insight: cf_clearance cookie bypasses challenge page.
Submit form through browser (not API), let CF handle it naturally.
"""
from playwright.sync_api import sync_playwright
import time, json, requests

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

TWOCAPTCHA_KEY = "3da28555894fd89bb569b748731e9400"
SITEKEY = "0x4AAAAAAAJel0iaAR3mgkjp"
PAGE_URL = "https://dash.cloudflare.com/sign-up"
CHROMIUM = "/snap/chromium/current/usr/lib/chromium-browser/chrome"
PROXY_USER = "brd-customer-hl_c0f6789c-zone-web_unlocker1"
PROXY_PASS = "ds3ovbwhs69y"
PROXY = {'server': 'http://brd.superproxy.io:33335', 'username': PROXY_USER, 'password': PROXY_PASS}
PROXY_STR = f"http://{PROXY_USER}:{PROXY_PASS}@brd.superproxy.io:33335"
CHROME_ARGS = ["--no-sandbox","--disable-setuid-sandbox","--ignore-certificate-errors","--allow-running-insecure-content","--ignore-certificate-errors-spki-list=*"]

def solve():
    log("Solving Turnstile...")
    r = requests.get(f"http://2captcha.com/in.php?key={TWOCAPTCHA_KEY}&method=turnstile&pageurl={PAGE_URL}&sitekey={SITEKEY}&json=1", timeout=15)
    result = r.json()
    if result.get('status') != 1:
        log(f"Failed: {result}")
        return None
    job_id = result['request']
    for i in range(40):
        time.sleep(3)
        r2 = requests.get(f"http://2captcha.com/res.php?key={TWOCAPTCHA_KEY}&action=get&id={job_id}&json=1", timeout=10)
        res = r2.json()
        if res.get('status') == 1:
            log(f"Token: {res['request'][:50]}...")
            return res['request']
        if 'CAPCHA_NOT_READY' not in str(res):
            log(f"Error: {res}")
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
        
        # Inject token to trigger challenge resolution
        page.evaluate(f'''() => {{
            window.cf_challenge_response = "{token}";
            window._cf_challenge_response = "{token}";
        }}''')
        
        # Wait for cf_clearance (the cookie that proves challenge resolved)
        for i in range(20):
            cookies = {c["name"]: c["value"] for c in ctx.cookies()}
            if 'cf_clearance' in cookies:
                log(f"cf_clearance: YES! ({i*2}s)")
                break
            time.sleep(2)
        else:
            log("Warning: no cf_clearance cookie")
        
        all_cookies = ctx.cookies()
        
        # Fill form
        email_inp = page.query_selector('input[name="email"]')
        if not email_inp or not email_inp.is_visible():
            log("No email input!")
            page.screenshot(path='/tmp/cf_nofield.png')
            browser.close()
            return
        
        log("Filling form...")
        email_inp.fill(email)
        time.sleep(0.5)
        pw_inp = page.query_selector('input[name="password"]')
        pw_inp.fill(pw)
        time.sleep(0.5)
        
        # Track what happens on submit
        captured_res = [None]
        captured_req = [None]
        def on_req(req):
            if 'user/create' in req.url:
                captured_req[0] = req
        def on_res(resp):
            if 'user/create' in resp.url:
                captured_res[0] = resp
        page.on("request", on_req)
        page.on("response", on_res)
        
        log("Submitting...")
        page.click('button[type="submit"]')
        
        # Wait for navigation or response
        time.sleep(15)
        
        final_url = page.url
        final_title = page.title()
        log(f"\nFinal URL: {final_url}")
        log(f"Final title: {final_title}")
        
        # Check the API response
        if captured_res[0]:
            status = captured_res[0].status
            try:
                body = captured_res[0].json()
                if body.get('success'):
                    log("===== API SUCCESS! Account created! =====")
                    log(f"Account: {email}")
                else:
                    code = body.get('errors', [{}])[0].get('code')
                    msg = body.get('errors', [{}])[0].get('message')
                    log(f"API error {code}: {msg}")
            except:
                log(f"API response ({status}): {captured_res[0].text[:200]}")
        else:
            log("No API response captured")
        
        # Check for verify email page
        if 'verify' in final_url.lower() or 'check' in final_url.lower():
            log("===== VERIFY EMAIL PAGE! =====")
            log("Account creation SUCCESS!")
        
        page.screenshot(path='/tmp/cf_simple.png')
        browser.close()

def main():
    log("=== CF Signup - SIMPLE METHOD ===")
    token = solve()
    if token:
        signup(token)
    log("\nDone")

if __name__ == '__main__':
    main()