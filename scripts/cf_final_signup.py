#!/usr/bin/env python3
"""CF signup - use modified HTML from Bright Data + browser"""
from camoufox import Camoufox
import time, re, requests

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

BRD = {
    'http': 'http://brd-customer-hl_c0f6789c-zone-web_unlocker1:ds3ovbwhs69y@brd.superproxy.io:33335',
    'https': 'http://brd-customer-hl_c0f6789c-zone-web_unlocker1:ds3ovbwhs69y@brd.superproxy.io:33335'
}

email = f"finaltest{int(time.time())}@hilmal.store"
pw = "FinalTest123!"
log(f"Email: {email}")

# Step 1: Get page via requests (via Bright Data)
log("=== Step 1: Get page via Bright Data ===")
session = requests.Session()
session.proxies = BRD
session.verify = False
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
})

r = session.get('https://dash.cloudflare.com/sign-up', timeout=30)
log(f"Page status: {r.status_code}")

# Extract challenge params
challenge_match = re.search(r'window\.__CF\$cv\$params\s*=\s*(\{[^;]+\})', r.text)
if challenge_match:
    challenge_params = challenge_match.group(1)
    log(f"Challenge params found: {challenge_params[:80]}")
    
    # Extract cf_challenge_response from the page
    # Check if there's a cf_clearance cookie already
    cf_clearance = session.cookies.get('cf_clearance')
    log(f"cf_clearance cookie: {cf_clearance[:30] if cf_clearance else 'None'}")

# Check cookies
cookies = session.cookies.get_dict()
log(f"Cookies: {list(cookies.keys())}")

# Step 2: Try using modified HTML directly in browser
log("=== Step 2: Browser with modified HTML ===")
with Camoufox(headless=True, geoip=False) as browser:
    ctx = browser.new_context()
    page = ctx.new_page()
    
    # Inject all cookies from requests session
    for name, value in cookies.items():
        for domain in ['.dash.cloudflare.com', '.cloudflare.com']:
            try:
                ctx.add_cookies([{'name': name, 'value': value, 'domain': domain, 'path': '/'}])
            except:
                pass
    
    # Inject challenge params
    page.add_init_script(f"""
        window.__CF$cv$params = {challenge_params};
        console.log('Challenge params injected:', window.__CF$cv$params);
    """)
    
    page.goto("https://dash.cloudflare.com/sign-up", timeout=60000)
    time.sleep(5)
    
    title = page.title()
    url = page.url
    body = page.inner_text('body')
    
    log(f"Page: {title} | {url}")
    
    if 'dashboard' in title.lower() and 'sign-up' not in url:
        log("SUCCESS!")
    elif 'let us know' in body.lower():
        log("Challenge shown - try to interact with it")
        # Wait for challenge to auto-solve
        time.sleep(15)
        
        if 'dashboard' in page.title().lower():
            log("SUCCESS after challenge wait!")
        else:
            body2 = page.inner_text('body')
            log(f"Still challenged: {body2[:100]}")
            page.screenshot(path='/tmp/cf_final_challenge.png')
    elif 'email' in body.lower() and 'password' in body.lower():
        log("Signup form loaded! Fill and submit...")
        page.fill('input[name="email"]', email)
        page.fill('input[name="password"]', pw)
        time.sleep(0.5)
        page.click('button[type="submit"]')
        log("Clicked submit...")
        time.sleep(10)
        
        if 'dashboard' in page.title().lower():
            log("SUCCESS!")
            page.screenshot(path='/tmp/cf_final_success.png')
        else:
            body2 = page.inner_text('body')
            log(f"Result: {body2[:200]}")
    else:
        log(f"Other: {body[:100]}")
    
    browser.close()

log("=== Done ===")