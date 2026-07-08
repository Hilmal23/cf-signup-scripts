#!/usr/bin/env python3
"""CF signup - pre-cookied context approach"""
from camoufox import Camoufox
import time, json

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

COOKIE_FILE = '/root/cf_cookies.json'

# Step 1: Get authenticated cookies
log("=== Step 1: Getting authenticated cookies ===")

# First, login to CF with credentials
CF_EMAIL = "tengkeikmal@gmail.com"
CF_PASS = "CfMail2024!"

with Camoufox(headless=True, geoip=False) as browser:
    ctx = browser.new_context()
    page = ctx.new_page()
    
    # Login first
    page.goto("https://dash.cloudflare.com/login", timeout=60000)
    time.sleep(3)
    
    # Fill login form
    try:
        page.fill('input[name="email"]', CF_EMAIL)
        page.fill('input[name="password"]', CF_PASS)
        time.sleep(1)
        page.click('button[type="submit"]')
        time.sleep(5)
        log(f"Login result: {page.title()} | {page.url}")
        
        if 'dashboard' in page.url.lower() or 'overview' in page.url.lower():
            log("LOGIN SUCCESS!")
        else:
            log(f"Login page content: {page.inner_text('body')[:300]}")
    except Exception as e:
        log(f"Login error: {e}")
    
    # Get all cookies from authenticated session
    cookies = ctx.cookies()
    log(f"Cookies after login: {len(cookies)}")
    for c in cookies:
        log(f"  {c['name']}: {c['value'][:30]}")
    
    # Save cookies
    with open(COOKIE_FILE, 'w') as f:
        json.dump(cookies, f)
    log(f"Saved cookies to {COOKIE_FILE}")
    
    browser.close()

# Step 2: Use cookies to create new account
log("=== Step 2: Creating account with pre-cookied context ===")
email = f"precooked{int(time.time())}@hilmal.store"
pw = "Precooked123!"
log(f"Email: {email}")

# Load saved cookies
try:
    with open(COOKIE_FILE, 'r') as f:
        saved_cookies = json.load(f)
    log(f"Loaded {len(saved_cookies)} cookies")
except Exception as e:
    log(f"No saved cookies: {e}")
    saved_cookies = []

if saved_cookies:
    with Camoufox(headless=True, geoip=False) as browser:
        ctx = browser.new_context()
        
        # Set saved cookies
        ctx.add_cookies(saved_cookies)
        log("Cookies injected into new context")
        
        page = ctx.new_page()
        page.goto("https://dash.cloudflare.com/sign-up", timeout=60000)
        time.sleep(5)
        
        title = page.title()
        url = page.url
        body = page.inner_text('body')
        
        log(f"Result: {title} | {url}")
        
        if 'dashboard' in title.lower() and 'sign-up' not in url:
            log("SUCCESS - authenticated session!")
        elif 'let us know' in body.lower() or 'verify you are human' in body.lower():
            log("CAPTCHA challenge shown despite cookies")
        elif 'let us know' in body.lower():
            log("Challenge shown")
        else:
            log(f"Other: {body[:200]}")
        
        browser.close()
else:
    log("No cookies to use")

log("=== Done ===")