#!/usr/bin/env python3
"""
CF Signup - SESSION TRANSFER (ultimate approach)
1. Visit signup page → get cf_clearance cookie (Turnstile was solved by 2Captcha)
2. Create requests.Session with those cookies
3. Send signup API via SAME session (cookies + IP match)
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
        
        log("Loading signup page (gets challenge + cookies)...")
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
        
        # Inject token to trigger challenge resolution (gets cf_clearance cookie)
        page.evaluate(f'''() => {{
            window.cf_challenge_response = "{token}";
            window._cf_challenge_response = "{token}";
        }}''')
        
        # Wait for cf_clearance
        for i in range(20):
            cookies = {c["name"]: c["value"] for c in ctx.cookies()}
            if 'cf_clearance' in cookies:
                log(f"cf_clearance: YES! ({i*2}s)")
                break
            time.sleep(2)
        else:
            log("Warning: no cf_clearance")
        
        all_cookies = ctx.cookies()
        
        # Get security_token from hidden field
        security_token = page.evaluate('''() => {{
            var inp = document.querySelector('input[name="security_token"]');
            return inp ? inp.value : "";
        }}''')
        log(f"Security token: {security_token[:30]}...")
        
        # Extract ALL cookies
        cookie_list = []
        for c in all_cookies:
            cookie_list.append({
                'name': c['name'],
                'value': c['value'],
                'domain': c.get('domain', '.cloudflare.com'),
                'path': c.get('path', '/'),
            })
            if c['name'] in ['cf_clearance', '__cf_bm', '__cflb']:
                log(f"Cookie {c['name']}: {c['value'][:40]}...")
        
        log(f"\nTotal cookies: {len(cookie_list)}")
        
        # Create requests session WITH those cookies
        session = requests.Session()
        session.verify = False
        session.proxies = {'http': PROXY_STR, 'https': PROXY_STR}
        
        # Add cookies to session
        for c in cookie_list:
            session.cookies.set(c['name'], c['value'], domain=c.get('domain'), path=c.get('path'))
        
        # Headers matching browser
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Content-Type': 'application/json',
            'Origin': 'https://dash.cloudflare.com',
            'Referer': 'https://dash.cloudflare.com/sign-up',
        })
        
        # Try 1: WITHOUT cf_challenge_response (just cookies)
        log("\n=== Try 1: Session (no token) ===")
        data1 = {
            "email": email,
            "password": pw,
            "mrk_optin": True,
            "security_token": security_token,
            "method": "Onboarding: New_v2",
            "locale": "en-US",
            "legal_stamp": "",
            "opt_ins": {},
            "mrktCheckboxDisplayed": False,
            "hCaptchaDisplayed": False,
        }
        
        r1 = session.post('https://dash.cloudflare.com/api/v4/user/create', json=data1, timeout=30)
        log(f"Status: {r1.status_code}")
        log(f"Response: {r1.text[:400]}")
        try:
            resp1 = r1.json()
            if resp1.get('success'):
                log("===== SUCCESS! =====")
                log(f"Account: {email}")
                page.screenshot(path='/tmp/cf_success.png')
                browser.close()
                return
            code1 = resp1.get('errors', [{}])[0].get('code')
            msg1 = resp1.get('errors', [{}])[0].get('message')
            log(f"Error {code1}: {msg1}")
        except:
            pass
        
        # Try 2: WITH token in body
        log("\n=== Try 2: Session (WITH token) ===")
        data2 = dict(data1)
        data2['cf_challenge_response'] = token
        
        r2 = session.post('https://dash.cloudflare.com/api/v4/user/create', json=data2, timeout=30)
        log(f"Status: {r2.status_code}")
        log(f"Response: {r2.text[:400]}")
        try:
            resp2 = r2.json()
            if resp2.get('success'):
                log("===== SUCCESS! =====")
                log(f"Account: {email}")
                page.screenshot(path='/tmp/cf_success.png')
                browser.close()
                return
            code2 = resp2.get('errors', [{}])[0].get('code')
            msg2 = resp2.get('errors', [{}])[0].get('message')
            log(f"Error {code2}: {msg2}")
        except:
            pass
        
        # Try 3: Without cf_challenge_response key entirely
        log("\n=== Try 3: Session (no token key) ===")
        r3 = session.post('https://dash.cloudflare.com/api/v4/user/create', json=data1, timeout=30)
        log(f"Status: {r3.status_code}")
        
        page.screenshot(path='/tmp/cf_session.png')
        browser.close()

def main():
    log("=== CF Signup - SESSION TRANSFER ===")
    token = solve()
    if token:
        signup(token)
    log("\nDone")

if __name__ == '__main__':
    main()