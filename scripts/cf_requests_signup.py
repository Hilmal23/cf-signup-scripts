#!/usr/bin/env python3
"""CF signup - Python requests + browser cookie injection"""
from camoufox import Camoufox
import time, re, requests

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

BRD = {
    'http': 'http://brd-customer-hl_c0f6789c-zone-web_unlocker1:ds3ovbwhs69y@brd.superproxy.io:33335',
    'https': 'http://brd-customer-hl_c0f6789c-zone-web_unlocker1:ds3ovbwhs69y@brd.superproxy.io:33335'
}

email = f"reqtest{int(time.time())}@hilmal.store"
pw = "Reqtest123!"

log(f"Email: {email}")

# Step 1: Get CF page via requests (SSL bypass works)
log("=== Step 1: Get CF page + cookies via requests ===")
session = requests.Session()
session.proxies = BRD
session.verify = False  # Bypass MITM cert
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
})

try:
    r = session.get('https://dash.cloudflare.com/sign-up', timeout=30)
    log(f"CF page: {r.status_code} | {r.url}")
    
    # Extract hidden fields
    security_token = re.search(r'name="security_token".*?value="([^"]+)"', r.text)
    log(f"Security token: {security_token.group(1)[:20] if security_token else 'None'}")
    
    # Get cookies
    cookie_dict = {k: v for k, v in session.cookies.get_dict().items()}
    log(f"Cookies: {list(cookie_dict.keys())}")
    
    # Check for challenge
    if 'challenge' in r.text.lower() or 'cloudflare' in r.text.lower():
        log("CF challenge JS present in page")
        # Extract the challenge widget info
        sitekey_match = re.search(r'data-sitekey="([^"]+)"', r.text)
        log(f"Sitekey: {sitekey_match.group(1) if sitekey_match else 'None'}")
    
except Exception as e:
    log(f"Step 1 error: {e}")

# Step 2: Submit form via requests
log("=== Step 2: Submit form via requests ===")
try:
    form_data = {
        'email': email,
        'password': pw,
        'security_token': security_token.group(1) if security_token else '',
        'cf_challenge_response': '',
        'redirect_uri': '',
        'sso': '',
        'sig': '',
    }
    
    r2 = session.post('https://dash.cloudflare.com/sign-up', data=form_data, timeout=30, allow_redirects=True)
    log(f"POST result: {r2.status_code} | {r2.url}")
    log(f"Response: {r2.text[:300]}")
    
    if 'dashboard' in r2.url.lower():
        log("SUCCESS via requests!")
    else:
        log(f"Response URL: {r2.url}")
        
except Exception as e:
    log(f"Step 2 error: {e}")

# Step 3: If requests approach fails, use browser with injected cookies
log("=== Step 3: Browser with requests cookies ===")
with Camoufox(headless=True, geoip=False) as browser:
    ctx = browser.new_context(
        proxy={'server': 'http://brd.superproxy.io:33335', 'username': 'brd-customer-hl_c0f6789c-zone-web_unlocker1', 'password': 'ds3ovbwhs69y'}
    )
    page = ctx.new_page()
    
    # Inject cookies from requests session
    for name, value in cookie_dict.items():
        ctx.add_cookies([{'name': name, 'value': value, 'domain': '.dash.cloudflare.com', 'path': '/'}])
    
    page.goto("https://dash.cloudflare.com/sign-up", timeout=60000)
    time.sleep(5)
    
    title = page.title()
    url = page.url
    body = page.inner_text('body')
    
    log(f"Browser result: {title} | {url}")
    
    if 'dashboard' in title.lower() and 'sign-up' not in url:
        log("SUCCESS via browser with injected cookies!")
    elif 'let us know' in body.lower():
        log("Challenge still shown")
    elif 'email' in body.lower() and 'password' in body.lower():
        log("Signup form loaded (cookies not logged in)")
        page.fill('input[name="email"]', email)
        page.fill('input[name="password"]', pw)
        time.sleep(0.5)
        page.click('button[type="submit"]')
        log("Clicked submit...")
        time.sleep(10)
        
        if 'dashboard' in page.title().lower():
            log("SUCCESS!")
        else:
            log(f"Result: {page.inner_text('body')[:200]}")
    else:
        log(f"Other: {body[:100]}")
    
    browser.close()

log("=== Done ===")