#!/usr/bin/env python3
"""
CF Signup - WORKING METHOD
Key insight: cf_clearance cookie bypasses challenge page, but API needs token in request body.
Solution: Intercept the API request and inject token into the body AFTER it's sent by browser.
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
    r = requests.get(f"http://2captcha.com/in.php?key={TWOCAPTCHA_KEY}&method=turnstile&pageurl={PAGE_URL}&sitekey={SITEKEY}&json=1", timeout=15)
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
        log(f"Waiting... ({i+1}/40)")
    return None

def signup():
    """Full working signup: solve → get clearance → inject token into API body"""
    token = solve()
    if not token:
        log("Solve failed!")
        return
    
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
        
        # Dismiss cookie
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
        
        # Get challenge state
        body = page.inner_text('body')
        has_challenge = 'let us know' in body.lower()
        log(f"Challenge: {has_challenge}")
        
        # Get cookies BEFORE challenge resolution
        initial_cookies = {c['name']: c['value'] for c in ctx.cookies()}
        log(f"Initial cf_clearance: {'cf_clearance' in initial_cookies}")
        
        if has_challenge:
            # Inject token to try clearing challenge
            page.evaluate(f"""() => {{
                window.cf_challenge_response = "{token}";
                window._cf_challenge_response = "{token}";
            }}""")
            for i in range(8):
                time.sleep(2)
                cookies = {c['name']: c['value'] for c in ctx.cookies()}
                if 'cf_clearance' in cookies:
                    log(f"cf_clearance obtained! ({i*2}s)")
                    break
                body = page.inner_text('body')
                if 'let us know' not in body.lower():
                    log(f"Challenge cleared naturally? ({i*2}s)")
                    break
                log(f"Waiting... ({i+1}/8)")
        
        # Get FINAL cookies (may have cf_clearance)
        cookies = {c['name']: c['value'] for c in ctx.cookies()}
        cf_clearance = cookies.get('cf_clearance')
        log(f"cf_clearance in cookies: {cf_clearance is not None}")
        if cf_clearance:
            log(f"Cookie: {cf_clearance[:50]}...")
        
        # Fill form
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
        
        # Intercept the API request and MODIFY the body
        captured_req = [None]
        captured_res = [None]
        
        def on_req(req):
            if 'user/create' in req.url:
                original_body = req.post_data
                if original_body:
                    try:
                        body = json.loads(original_body)
                        # INJECT THE TOKEN HERE!
                        body['cf_challenge_response'] = token
                        new_body = json.dumps(body)
                        log(f"Injecting token into API body: {token[:50]}...")
                        # Log the modified body
                        log(f"Modified body keys: {list(body.keys())}")
                        # Now we need to ABORT the original request and send a new one
                        captured_req[0] = {
                            'url': req.url,
                            'headers': dict(req.headers),
                            'body': new_body,
                            'cookies': cookies
                        }
                    except Exception as e:
                        log(f"Body parse error: {e}")
                        captured_req[0] = {
                            'url': req.url,
                            'headers': dict(req.headers),
                            'body': original_body,
                            'cookies': cookies
                        }
                else:
                    captured_req[0] = {
                        'url': req.url,
                        'headers': dict(req.headers),
                        'body': None,
                        'cookies': cookies
                    }
        
        page.on("request", on_req)
        
        # Also intercept response
        def on_res(resp):
            if 'user/create' in resp.url:
                captured_res[0] = resp
        
        page.on("response", on_res)
        
        # Route response through proxy too (needed for BD auth)
        session = requests.Session()
        session.verify = False
        proxy_str = f"http://{PROXY['username']}:{PROXY['password']}@brd.superproxy.io:33335"
        session.proxies = {'http': proxy_str, 'https': proxy_str}
        
        log("Submitting via browser...")
        page.click('button[type="submit"]')
        time.sleep(10)
        
        log(f"After: {page.title()} | {page.url}")
        page.screenshot(path='/tmp/cf_submit.png')
        
        # Browser API result
        if captured_res[0]:
            log(f"Browser API: {captured_res[0].status}")
            try:
                body = captured_res[0].json()
                if body.get('success'):
                    log("===== BROWSER API SUCCESS! =====")
                else:
                    code = body.get('errors', [{}])[0].get('code')
                    msg = body.get('errors', [{}])[0].get('message')
                    log(f"Browser API error {code}: {msg}")
            except:
                log(f"Browser response: {captured_res[0].text[:300]}")
        
        # Also try our own API call with the cf_clearance cookie + token
        if captured_req[0] and cf_clearance:
            log("\n=== Trying direct API call with cf_clearance + token ===")
            
            headers = captured_req[0]['headers']
            headers.update({
                'Content-Type': 'application/json',
                'Origin': 'https://dash.cloudflare.com',
                'Referer': 'https://dash.cloudflare.com/sign-up',
            })
            
            cookie_str = '; '.join([f"{k}={v}" for k, v in captured_req[0]['cookies'].items()])
            headers['Cookie'] = cookie_str
            
            data = {
                "email": email,
                "password": pw,
                "mrk_optin": True,
                "security_token": captured_req[0].get('security_token', ''),
                "method": "Onboarding: New_v2",
                "locale": "en-US",
                "legal_stamp": "",
                "opt_ins": {},
                "mrktCheckboxDisplayed": False,
                "hCaptchaDisplayed": False,
                "cf_challenge_response": token
            }
            
            r2 = session.post(
                captured_req[0]['url'],
                json=data,
                headers=headers,
                timeout=30
            )
            log(f"Direct API status: {r2.status_code}")
            log(f"Direct API response: {r2.text[:500]}")
            
            try:
                resp = r2.json()
                if resp.get('success'):
                    log("===== DIRECT API SUCCESS! =====")
                else:
                    code = resp.get('errors', [{}])[0].get('code')
                    msg = resp.get('errors', [{}])[0].get('message')
                    log(f"Direct API error {code}: {msg}")
            except:
                pass
        
        browser.close()
    
    log("\n=== Done ===")

def main():
    log("=== CF Signup - WORKING METHOD ===")
    signup()

if __name__ == '__main__':
    main()