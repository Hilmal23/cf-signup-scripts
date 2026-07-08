#!/usr/bin/env python3
"""
CF Signup - Browser Submit (no requests transfer)
Submit form within the SAME browser that solved Turnstile.
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

def test_browser_submit():
    email = f"cf{int(time.time()*1000)}@hilmal.store"
    pw = "CfSignup123!"
    log(f"Email: {email}")
    
    token = solve()
    if not token:
        return None
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=CHROMIUM, args=CHROME_ARGS)
        ctx = browser.new_context(proxy=PROXY)
        page = ctx.new_page()
        
        log("Loading signup page...")
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
        
        # Wait for cf_clearance (injected via token)
        page.evaluate(f"window.cf_challenge_response = '{token}'; window._cf_challenge_response = '{token}';")
        
        for i in range(10):
            cookies = {c["name"]: c["value"] for c in ctx.cookies()}
            if 'cf_clearance' in cookies:
                log(f"cf_clearance: YES ({i*2}s)")
                break
            time.sleep(2)
        
        # Fill form
        email_inp = page.query_selector('input[name="email"]')
        if not email_inp or not email_inp.is_visible():
            log("No email input!")
            browser.close()
            return None
        
        email_inp.fill(email)
        time.sleep(0.3)
        pw_inp = page.query_selector('input[name="password"]')
        pw_inp.fill(pw)
        time.sleep(0.3)
        
        # Track response
        captured_res = [None]
        def on_res(resp):
            if 'user/create' in resp.url:
                captured_res[0] = resp
        page.on("response", on_res)
        
        log("Submitting via button click...")
        page.click('button[type="submit"]')
        
        # Monitor for 20 seconds
        for i in range(20):
            time.sleep(1)
            url = page.url
            body = page.inner_text('body')
            
            if 'dashboard' in url.lower() and 'sign-up' not in url:
                log("===== DASHBOARD! =====")
                page.screenshot(path='/tmp/cf_dashboard.png')
                browser.close()
                return email
            
            if 'EMAIL ALREADY' in body.upper():
                log("===== EMAIL TAKEN! =====")
                page.screenshot(path='/tmp/cf_taken.png')
                browser.close()
                return email
            
            if 'VERIF' in body.upper() and 'EMAIL' in body.upper():
                log("===== VERIFY EMAIL! =====")
                page.screenshot(path='/tmp/cf_verify2.png')
                browser.close()
                return email
            
            if i % 5 == 0:
                log(f"  [{i}s] {page.title()[:40]}")
        
        if captured_res[0]:
            try:
                body = captured_res[0].json()
                code = body.get('errors', [{}])[0].get('code')
                msg = body.get('errors', [{}])[0].get('message')
                log(f"API error {code}: {msg}")
            except:
                pass
        
        page.screenshot(path='/tmp/cf_final2.png')
        browser.close()
        return None

def main():
    log("=== CF Signup - Browser Submit ===")
    result = test_browser_submit()
    if result:
        log(f"===== POTENTIAL: {result} =====")
    else:
        log("Failed")
    log("\nDone")

if __name__ == '__main__':
    main()