#!/usr/bin/env python3
"""
CF Signup - Camoufox (Firefox) approach
Key: Camoufox uses Firefox with anti-detection fingerprints.
Firefox might render Turnstile iframe differently.
Also try: disable_coop=True to click iframe checkbox manually.
"""
import camoufox, time, json, requests

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

TWOCAPTCHA_KEY = "3da28555894fd89bb569b748731e9400"
SITEKEY = "0x4AAAAAAAJel0iaAR3mgkjp"
PAGE_URL = "https://dash.cloudflare.com/sign-up"

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
        log(f"Waiting... ({i+1}/40)")
    return None

def signup(token):
    email = f"cf{int(time.time()*1000)}@hilmal.store"
    pw = "CfSignup123!"
    log(f"Email: {email}")
    
    with camoufox.Camoufox(
        headless=True,
        geoip=False,
        disable_coop=True,
        i_know_what_im_doing=True,
    ) as browser:
        page = browser.new_page()
        
        log("Loading page...")
        page.goto(PAGE_URL, timeout=60000)
        time.sleep(10)
        
        # Dismiss cookie consent
        for _ in range(5):
            try:
                allow = page.get_by_text("Allow All")
                if allow.is_visible():
                    allow.click()
                    time.sleep(1)
                    break
            except:
                pass
            time.sleep(1)
        
        # Check page state
        body = page.inner_text('body')
        has_challenge = 'let us know' in body.lower()
        log(f"Has challenge: {has_challenge}")
        
        # Check for Turnstile iframe
        iframe = page.query_selector('iframe[src*="turnstile"]')
        log(f"Turnstile iframe: {iframe is not None}")
        
        if has_challenge:
            # Inject token
            page.evaluate(f"""() => {{
                window.cf_challenge_response = "{token}";
                window._cf_challenge_response = "{token}";
            }}""")
            
            # Try clicking the Turnstile checkbox
            try:
                checkbox = page.query_selector('.challenge-form input[type="checkbox"]')
                if checkbox:
                    checkbox.click()
                    log("Clicked challenge checkbox")
            except Exception as e:
                log(f"Click error: {e}")
            
            # Wait for challenge to clear
            for i in range(10):
                time.sleep(2)
                body = page.inner_text('body')
                if 'let us know' not in body.lower():
                    log(f"Challenge cleared! ({i*2}s)")
                    break
                log(f"Waiting... ({i+1}/10)")
        
        # Check cookies
        ctx = page.context
        cookies = ctx.cookies()
        cf_clearance = None
        for c in cookies:
            if c['name'] == 'cf_clearance':
                cf_clearance = c['value']
                log(f"cf_clearance: {c['value'][:50]}...")
        
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
        
        # Track response
        captured = [None]
        def on_res(resp):
            if 'user/create' in resp.url:
                captured[0] = resp
        page.on("response", on_res)
        
        log("Submitting...")
        page.click('button[type="submit"]')
        time.sleep(10)
        
        log(f"After: {page.title()} | {page.url}")
        
        if captured[0]:
            log(f"API: {captured[0].status}")
            try:
                body = captured[0].json()
                if body.get('success'):
                    log("===== SUCCESS! =====")
                    log(f"Account: {email}")
                else:
                    code = body.get('errors', [{}])[0].get('code')
                    msg = body.get('errors', [{}])[0].get('message')
                    log(f"Error {code}: {msg}")
            except:
                log(f"Response: {captured[0].text[:300]}")
        
        page.screenshot(path='/tmp/cf_camoufox.png')
        browser.close()

def main():
    log("=== CF Signup - Camoufox Firefox ===")
    token = solve()
    if token:
        signup(token)
    log("\nDone")

if __name__ == '__main__':
    main()