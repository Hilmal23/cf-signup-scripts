#!/usr/bin/env python3
"""
CF Signup - Test IP binding theory
1. Solve via 2Captcha (direct from Kamatera, no proxy)
2. Browser uses BD proxy
3. Test: does token work from different IP?
"""
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

def solve_direct():
    """Solve Turnstile DIRECTLY from Kamatera (no proxy)"""
    log("=== Solving Turnstile DIRECT (no proxy) ===")
    r = requests.get(
        f"http://2captcha.com/in.php?key={TWOCAPTCHA_KEY}&method=turnstile&pageurl={PAGE_URL}&sitekey={SITEKEY}&json=1",
        timeout=15
    )
    result = r.json()
    if result.get('status') != 1:
        log(f"Submit failed: {result}")
        return None
    job_id = result['request']
    log(f"Job: {job_id}")
    for i in range(40):
        time.sleep(3)
        r2 = requests.get(
            f"http://2captcha.com/res.php?key={TWOCAPTCHA_KEY}&action=get&id={job_id}&json=1",
            timeout=10
        )
        res = r2.json()
        if res.get('status') == 1:
            log(f"Token: {res['request'][:50]}...")
            return res['request']
        if 'CAPCHA_NOT_READY' not in str(res):
            log(f"Error: {res}")
            return None
        log(f"Waiting... ({i+1}/40)")
    return None

def signup_with_browser(token):
    """Signup with browser (uses BD proxy)"""
    email = f"cf{int(time.time()*1000)}@hilmal.store"
    pw = "CfSignup123!"
    log(f"\nEmail: {email}")
    
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
        
        body = page.inner_text('body')
        has_challenge = 'let us know' in body.lower()
        log(f"Challenge: {has_challenge}")
        
        if has_challenge:
            page.evaluate(f"""() => {{
                window.cf_challenge_response = "{token}";
                window._cf_challenge_response = "{token}";
            }}""")
            for i in range(8):
                time.sleep(2)
                body = page.inner_text('body')
                if 'let us know' not in body.lower():
                    log(f"Challenge cleared! ({i*2}s)")
                    break
                log(f"Waiting... ({i+1}/8)")
        
        # Check cookies
        cookies = ctx.cookies()
        cf_clearance = None
        for c in cookies:
            if c['name'] == 'cf_clearance':
                cf_clearance = c['value']
                log(f"cf_clearance: {c['value'][:50]}...")
        
        log(f"cf_clearance obtained: {cf_clearance is not None}")
        
        # Fill + submit
        email_inp = page.query_selector('input[name="email"]')
        if not email_inp or not email_inp.is_visible():
            log("No email input!")
            page.screenshot(path='/tmp/cf_nofield.png')
            browser.close()
            return
        
        email_inp.fill(email)
        time.sleep(0.3)
        pw_inp = page.query_selector('input[name="password"]')
        pw_inp.fill(pw)
        time.sleep(0.3)
        
        captured_req = [None]
        captured_res = [None]
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
        time.sleep(10)
        
        log(f"After: {page.title()} | {page.url}")
        page.screenshot(path='/tmp/cf_final.png')
        
        if captured_req[0]:
            try:
                body = json.loads(captured_req[0].post_data or '{}')
                log(f"cf_challenge_response sent: '{body.get('cf_challenge_response', 'EMPTY')[:60] if body.get('cf_challenge_response') else 'EMPTY'}'")
            except:
                log(f"Body: {captured_req[0].post_data[:100]}")
        
        if captured_res[0]:
            log(f"API: {captured_res[0].status}")
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
        
        browser.close()

def main():
    log("=== CF Signup - IP Test ===")
    log("Theory: token from 2Captcha datacenter IP, browser from residential")
    
    token = solve_direct()
    if not token:
        log("Solve failed!")
        return
    
    signup_with_browser(token)
    log("\n=== Done ===")

if __name__ == '__main__':
    main()