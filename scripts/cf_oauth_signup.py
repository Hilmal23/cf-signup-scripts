#!/usr/bin/env python3
"""CF signup via Google OAuth"""
from camoufox import Camoufox
import time, json

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

# Test Google OAuth signup
log("=== Testing Google OAuth signup ===")

with Camoufox(headless=True, geoip=False) as browser:
    ctx = browser.new_context()
    page = ctx.new_page()
    
    page.goto("https://dash.cloudflare.com/sign-up", timeout=30000)
    time.sleep(3)
    
    # Find Google button
    google_btns = page.query_selector_all('button, a, [role="button"]')
    for btn in google_btns:
        text = btn.inner_text().lower()
        href = (btn.get_attribute('href') or '').lower()
        if 'google' in text or 'google' in href:
            log(f"Google button: {btn.inner_text()} | {href}")
    
    # Try clicking "Continue with Google"
    try:
        page.click('text="Continue with Google"')
        time.sleep(5)
        log(f"After Google click: {page.url} | {page.title()}")
        body = page.inner_text('body')
        log(f"Body: {body[:500]}")
    except Exception as e:
        log(f"Google button click failed: {e}")
        
        # Try finding by href
        links = page.query_selector_all('a[href*="google"], button:has-text("Google")')
        for link in links:
            log(f"Link: {link.inner_text()} | {link.get_attribute('href')}")
    
    # Check current page state
    page.screenshot(path='/tmp/cf_oauth.png')
    log("Screenshot!")
    
    browser.close()

# Also check if CF has a partner/signup API
log("=== Checking CF Partner signup ===")
import requests
try:
    r = requests.get("https://dash.cloudflare.com/api/v4/account", timeout=10)
    log(f"CF API: {r.status_code}")
except Exception as e:
    log(f"API error: {e}")

# Test CF enterprise/partner endpoint
try:
    r = requests.post(
        "https://api.cloudflare.com/client/v4/register",
        json={"email": "test@test.com"},
        timeout=10
    )
    log(f"Register API: {r.status_code} | {r.text[:200]}")
except Exception as e:
    log(f"Register error: {e}")

log("=== Done ===")