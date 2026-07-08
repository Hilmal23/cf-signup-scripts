#!/usr/bin/env python3
"""
CF Signup - Direct API with Turnstile Token Injection
Key insight: The 2Captcha token was solved from a DIFFERENT IP (2Captcha datacenter).
The token might need to be injected directly into the API request body.
"""
from playwright.sync_api import sync_playwright
import time, json, requests, re

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

TWOCAPTCHA_KEY = "3da28555894fd89bb569b748731e9400"
SITEKEY = "0x4AAAAAAAJel0iaAR3mgkjp"
PAGE_URL = "https://dash.cloudflare.com/sign-up"
CHROMIUM = "/snap/chromium/current/usr/lib/chromium-browser/chrome"
PROXY = {'server': 'http://brd.superproxy.io:33335', 'username': 'brd-customer-hl_c0f6789c-zone-web_unlocker1', 'password': 'ds3ovbwhs69y'}
CHROME_ARGS = ["--no-sandbox","--disable-setuid-sandbox","--ignore-certificate-errors","--allow-running-insecure-content","--ignore-certificate-errors-spki-list=*"]

def solve():
    """Solve Turnstile"""
    log("Solving Turnstile...")
    r = requests.get(f"http://2captcha.com/in.php?key={TWOCAPTCHA_KEY}&method=turnstile&pageurl={PAGE_URL}&sitekey={SITEKEY}&json=1", timeout=10)
    result = r.json()
    if result.get('status') != 1:
        log(f"Submit failed: {result}")
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

def signup_v1_inject_to_form(token, email, pw):
    """Method 1: Inject token into browser form fields"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=CHROMIUM, args=CHROME_ARGS)
        ctx = browser.new_context(proxy=PROXY)
        page = ctx.new_page()
        
        page.goto(PAGE_URL, timeout=60000)
        time.sleep(10)
        
        # Dismiss cookie
        for _ in range(3):
            try:
                allow = page.query_selector('button:has-text("Allow All")')
                if allow and allow.is_visible():
                    allow.click()
                    time.sleep(1)
            except:
                pass
        
        # Inject token into every possible input
        page.evaluate(f"""
            () => {{
                window.cf_challenge_response = "{token}";
                window._cf_challenge_response = "{token}";
                document.querySelectorAll('input').forEach(inp => {{
                    if (inp.name && (
                        inp.name.includes('challenge') || 
                        inp.name.includes('cf_') || 
                        inp.name.includes('turnstile') ||
                        inp.name.includes('captcha')
                    )) {{
                        inp.value = "{token}";
                        inp.setAttribute('data-value', "{token}");
                    }}
                }});
            }}
        """)
        time.sleep(0.5)
        
        # Fill form + intercept request
        captured_req = [None]
        def on_req(req):
            if 'user/create' in req.url:
                captured_req[0] = {'headers': dict(req.headers), 'body': req.post_data}
        page.on("request", on_req)
        
        # Fill
        email_inp = page.query_selector('input[name="email"]')
        if not email_inp or not email_inp.is_visible():
            log("No email input!")
            return None
        
        email_inp.fill(email)
        time.sleep(0.3)
        pw_inp = page.query_selector('input[name="password"]')
        pw_inp.fill(pw)
        time.sleep(0.3)
        
        # Get security token
        sec = page.evaluate("() => document.querySelector('input[name=\"security_token\"]')?.value || ''")
        
        # Inject AFTER fill but BEFORE submit
        page.evaluate(f"""
            () => {{
                document.querySelectorAll('input').forEach(inp => {{
                    if (inp.name && (inp.name.includes('challenge') || inp.name.includes('cf_') || inp.name.includes('turnstile'))) {{
                        inp.value = "{token}";
                    }}
                }});
            }}
        """)
        time.sleep(0.3)
        
        page.click('button[type="submit"]')
        time.sleep(10)
        
        log(f"After: {page.title()} | {page.url}")
        
        if captured_req[0]:
            try:
                body = json.loads(captured_req[0]['body'])
                log(f"cf_challenge_response in request: '{body.get('cf_challenge_response', 'EMPTY')[:60] if body.get('cf_challenge_response') else 'EMPTY'}'")
            except:
                log(f"Body: {captured_req[0]['body'][:100]}")
        
        page.screenshot(path='/tmp/cf_inject.png')
        browser.close()

def signup_v2_direct_api(token, email, pw):
    """Method 2: Direct Python API call with token"""
    log(f"\n--- Direct API Method ---")
    log(f"Token: {token[:50]}...")
    
    session = requests.Session()
    session.verify = False
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Content-Type': 'application/json',
        'Origin': 'https://dash.cloudflare.com',
        'Referer': 'https://dash.cloudflare.com/sign-up',
    })
    
    # Get cookies + security token via browser
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=CHROMIUM, args=CHROME_ARGS)
        ctx = browser.new_context(proxy=PROXY)
        page = ctx.new_page()
        
        page.goto(PAGE_URL, timeout=60000)
        time.sleep(10)
        
        for _ in range(3):
            try:
                allow = page.query_selector('button:has-text("Allow All")')
                if allow and allow.is_visible():
                    allow.click()
                    time.sleep(1)
            except:
                pass
        
        # Get cookies
        cookies = ctx.cookies()
        cookie_dict = {c['name']: c['value'] for c in cookies}
        log(f"Cookies: {list(cookie_dict.keys())}")
        
        # Get security token
        sec = page.evaluate("() => document.querySelector('input[name=\"security_token\"]')?.value || ''")
        log(f"Security token: {sec[:30]}...")
        
        # Set cookies on requests session
        for name, value in cookie_dict.items():
            session.cookies.set(name, value, domain='.cloudflare.com', path='/')
        
        # Get legal_stamp
        legal_stamp = page.evaluate('''() => {
                    var inp = document.querySelector('input[name="legal_stamp"]');
                    return inp ? inp.value : '';
                }''')
        log(f"Legal stamp: {legal_stamp[:30]}...")
        
        browser.close()
    
    # Direct API POST with token
    data = {
        "email": email,
        "password": pw,
        "mrk_optin": True,
        "security_token": sec,
        "method": "Onboarding: New_v2",
        "locale": "en-US",
        "legal_stamp": legal_stamp,
        "opt_ins": {},
        "mrktCheckboxDisplayed": False,
        "hCaptchaDisplayed": False,
        "cf_challenge_response": token  # THE KEY FIELD
    }
    
    log(f"POST with cf_challenge_response: {token[:50]}...")
    r = session.post('https://dash.cloudflare.com/api/v4/user/create', json=data, timeout=30)
    log(f"Status: {r.status_code}")
    log(f"Response: {r.text[:500]}")
    
    if r.status_code == 200:
        log("SUCCESS!")
        return True
    
    try:
        err = r.json()
        if not err.get('success'):
            code = err.get('errors', [{}])[0].get('code')
            msg = err.get('errors', [{}])[0].get('message')
            log(f"Error {code}: {msg}")
    except:
        pass
    
    return False

def main():
    log("=== CF Signup - Direct API with Token ===")
    
    token = solve()
    if not token:
        log("Solve failed!")
        return
    
    email = f"cf{int(time.time()*1000)}@hilmal.store"
    pw = "CfSignup123!"
    log(f"Email: {email}")
    
    # Method 1: Browser form injection
    log("\n--- Method 1: Browser Form Injection ---")
    signup_v1_inject_to_form(token, email, pw)
    
    # Method 2: Direct API with cookies
    email2 = f"cf{int(time.time()*1000)}@hilmal.store"
    log(f"\n--- Method 2: Direct API (email: {email2}) ---")
    signup_v2_direct_api(token, email2, pw)
    
    log("\n=== Done ===")

if __name__ == '__main__':
    main()