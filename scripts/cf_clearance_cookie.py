#!/usr/bin/env python3
"""
CF Signup - USE cf_clearance COOKIE (not token!)
Key insight: After Turnstile solve, CF sets a cf_clearance COOKIE.
This cookie bypasses the challenge WITHOUT needing the token.
The cookie is valid for ~5 minutes.
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

def solve():
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

def signup_with_clearance_cookie():
    """
    Flow:
    1. Solve Turnstile via 2Captcha (get token)
    2. Open browser → navigate to CF signup
    3. Inject token into Turnstile iframe → triggers CF to set cf_clearance cookie
    4. Extract cf_clearance cookie
    5. Use cookie for API call (no more challenge needed)
    """
    token = solve()
    if not token:
        log("Solve failed!")
        return
    
    email = f"cf{int(time.time()*1000)}@hilmal.store"
    pw = "CfSignup123!"
    log(f"Email: {email}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=CHROMIUM, args=CHROME_ARGS)
        ctx = browser.new_context(proxy=PROXY)
        page = ctx.new_page()
        
        log("Loading signup page...")
        page.goto(PAGE_URL, timeout=60000)
        time.sleep(10)
        
        # Dismiss cookie consent
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
        
        # Check for Turnstile challenge
        body = page.inner_text('body')
        has_challenge = 'let us know' in body.lower()
        log(f"Has challenge: {has_challenge}")
        
        if has_challenge:
            log("Attempting to inject token into Turnstile...")
            # Try all possible injection methods
            result = page.evaluate(f"""
                () => {{
                    // Set global challenge response
                    window.cf_challenge_response = "{token}";
                    window._cf_challenge_response = "{token}";
                    window.CF_CHALLENGE_TOKEN = "{token}";
                    
                    // Try Turnstile object
                    if (typeof Turnstile !== 'undefined') {{
                        try {{
                            // Set it as a property
                            Object.defineProperty(window, 'cf_challenge_response', {{
                                value: "{token}",
                                writable: true,
                                configurable: true
                            }});
                            return 'Turnstile obj found, token set';
                        }} catch(e) {{
                            return 'Turnstile error: ' + e.message;
                        }}
                    }}
                    
                    // Try to find hidden inputs
                    var inputs = document.querySelectorAll('input');
                    for (var i = 0; i < inputs.length; i++) {{
                        var n = inputs[i].name || '';
                        var id = inputs[i].id || '';
                        if (n.includes('challenge') || n.includes('cf_') || id.includes('challenge')) {{
                            inputs[i].value = "{token}";
                            return 'Set input: ' + n;
                        }}
                    }}
                    return 'No input found';
                }}
            """)
            log(f"Injection result: {result}")
            
            # Wait for challenge to potentially resolve
            for i in range(8):
                time.sleep(2)
                body = page.inner_text('body')
                if 'let us know' not in body.lower():
                    log(f"Challenge cleared! ({i*2}s)")
                    break
                log(f"Waiting... ({i+1}/8)")
        
        # Check ALL cookies
        cookies = ctx.cookies()
        log(f"Total cookies: {len(cookies)}")
        
        cf_clearance = None
        cf_clearance_exp = None
        for c in cookies:
            if c['name'] == 'cf_clearance':
                cf_clearance = c['value']
                cf_clearance_exp = c.get('expires') or c.get('expiresUtc') or 'session'
                log(f"cf_clearance FOUND! value: {c['value'][:50]}...")
            else:
                log(f"  {c['name']}: {c['value'][:30]}...")
        
        # If we got cf_clearance, use it for direct API call
        if cf_clearance:
            log(f"\n=== Got cf_clearance cookie! Using for API... ===")
            
            # Get security token
            sec = page.evaluate('''() => {
                var el = document.querySelector('input[name="security_token"]');
                return el ? el.value : "";
            }''')
            log(f"Security token: {sec[:30]}...")
            
            # Get all relevant cookies as string
            cookie_str = '; '.join([f"{c['name']}={c['value']}" for c in cookies])
            
            # Direct API call WITH cf_clearance cookie
            session = requests.Session()
            session.verify = False
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Content-Type': 'application/json',
                'Origin': 'https://dash.cloudflare.com',
                'Referer': 'https://dash.cloudflare.com/sign-up',
                'Cookie': cookie_str,
            })
            
            # Use BD proxy for API call too
            session.proxies = {
                'http': f'http://{PROXY["username"]}:{PROXY["password"]}@{PROXY["server"].replace("http://","")}',
                'https': f'http://{PROXY["username"]}:{PROXY["password"]}@{PROXY["server"].replace("http://","")}'
            }
            
            data = {
                "email": email,
                "password": pw,
                "mrk_optin": True,
                "security_token": sec,
                "method": "Onboarding: New_v2",
                "locale": "en-US",
                "legal_stamp": "",
                "opt_ins": {},
                "mrktCheckboxDisplayed": False,
                "hCaptchaDisplayed": False,
                "cf_challenge_response": token
            }
            
            log("POSTing to /api/v4/user/create...")
            r = session.post('https://dash.cloudflare.com/api/v4/user/create', json=data, timeout=30)
            log(f"Status: {r.status_code}")
            log(f"Response: {r.text[:500]}")
            
            if r.status_code == 200:
                log("===== SUCCESS! Account created! =====")
            else:
                try:
                    err = r.json()
                    log(f"Error: {json.dumps(err, indent=2)}")
                except:
                    pass
        else:
            log("NO cf_clearance cookie! Token injection didn't work.")
            log("Trying to fill form anyway...")
            
            email_inp = page.query_selector('input[name="email"]')
            if email_inp and email_inp.is_visible():
                email_inp.fill(email)
                time.sleep(0.3)
                pw_inp = page.query_selector('input[name="password"]')
                pw_inp.fill(pw)
                time.sleep(0.3)
                page.click('button[type="submit"]')
                time.sleep(10)
                log(f"After: {page.title()} | {page.url}")
        
        page.screenshot(path='/tmp/cf_clearance_result.png')
        browser.close()
    
    log("\n=== Done ===")

def main():
    log("=== CF Signup - cf_clearance Cookie Method ===")
    signup_with_clearance_cookie()

if __name__ == '__main__':
    main()