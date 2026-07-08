#!/usr/bin/env python3
"""CF signup - Chrome through proxy with SSL bypass + cf_clearance extraction"""
from playwright.sync_api import sync_playwright
import time, requests

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

BRD_PROXY = 'http://brd-customer-hl_c0f6789c-zone-web_unlocker1:ds3ovbwhs69y@brd.superproxy.io:33335'

email = f"chromecf{int(time.time())}@hilmal.store"
pw = "Chromecf123!"
log(f"Email: {email}")

# Step 1: Get cf_clearance via multiple requests through Bright Data
log("=== Step 1: Get cf_clearance cookie ===")
session = requests.Session()
session.proxies = {
    'http': BRD_PROXY,
    'https': BRD_PROXY
}
session.verify = False
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
})

# Multiple requests to warm up and get cookies
for url in ['https://cloudflare.com', 'https://dash.cloudflare.com/', 'https://dash.cloudflare.com/sign-up']:
    try:
        r = session.get(url, timeout=30)
        log(f"  {url}: {r.status_code}")
    except Exception as e:
        log(f"  {url}: Error {e}")

all_cookies = session.cookies.get_dict()
log(f"Cookies: {list(all_cookies.keys())}")
log(f"cf_clearance: {all_cookies.get('cf_clearance', 'NONE')[:30] if all_cookies.get('cf_clearance') else 'NONE'}")

# Step 2: Try Chrome with proxy via command-line args
log("=== Step 2: Chrome through proxy ===")
with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        executable_path='/usr/bin/chromium-browser',
        args=[
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--ignore-certificate-errors',
            '--allow-running-insecure-content',
            '--disable-gpu',
            '--no-first-run',
            '--no-zygote',
            '--single-process',
            f'--proxy-server={BRD_PROXY}',
            '--proxy-bypass-list=localhost',
        ]
    )
    ctx = browser.new_context(ignore_https_errors=True)
    page = ctx.new_page()
    
    # Inject cookies
    for name, value in all_cookies.items():
        for domain in ['.dash.cloudflare.com', '.cloudflare.com']:
            try:
                ctx.add_cookies([{'name': name, 'value': value, 'domain': domain, 'path': '/'}])
            except:
                pass
    
    log("Navigating...")
    page.goto("https://dash.cloudflare.com/sign-up", timeout=90000)
    time.sleep(8)
    
    title = page.title()
    url = page.url
    body_text = page.evaluate("() => document.body ? document.body.innerText.substring(0, 200) : ''")
    
    log(f"Title: {title}")
    log(f"URL: {url}")
    log(f"Body: {body_text}")
    
    if 'dashboard' in title.lower() and 'sign-up' not in url:
        log("SUCCESS!")
    elif 'email' in body_text.lower() and 'password' in body_text.lower() and 'let us know' not in body_text.lower():
        log("Signup form loaded - NO challenge!")
        page.fill('input[name="email"]', email)
        page.fill('input[name="password"]', pw)
        time.sleep(0.5)
        page.click('button[type="submit"]')
        time.sleep(10)
        
        if 'dashboard' in page.title().lower():
            log("SUCCESS! Account created!")
            page.screenshot(path='/tmp/cf_chromecf_success.png')
        else:
            log(f"Result: {page.inner_text('body')[:200]}")
    else:
        log("Challenge shown")
        page.screenshot(path='/tmp/cf_chromecf_result.png')
    
    browser.close()

log("=== Done ===")