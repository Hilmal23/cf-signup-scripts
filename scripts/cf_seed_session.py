#!/usr/bin/env python3
"""Get authenticated session cookies from an established login"""
from camoufox import Camoufox
import time, json, os

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

# Create a NEW fresh login to get clean session cookies
# These will be used as seed for automation
email = f"autoseed{int(time.time())}@hilmal.store"
pw = "AutoSeed123!"

log(f"Creating seed session with {email}")

with Camoufox(headless=True, geoip=False) as browser:
    ctx = browser.new_context()
    page = ctx.new_page()
    
    page.goto("https://dash.cloudflare.com/sign-up", timeout=45000)
    time.sleep(5)
    
    # Fill signup form
    page.fill('input[name="email"]', email)
    time.sleep(0.5)
    page.fill('input[name="password"]', pw)
    time.sleep(0.5)
    page.click('button[type="submit"]')
    time.sleep(10)
    
    title = page.title()
    url = page.url
    log(f"After signup: {title} | {url}")
    
    body = page.inner_text('body')
    
    if 'dashboard' in title.lower() and 'sign up' not in url:
        log("SIGNUP SUCCESS! Extracting cookies and localStorage...")
        
        # Get ALL cookies
        cookies = ctx.cookies()
        cookie_json = json.dumps(cookies, indent=2)
        log(f"Cookies: {len(cookies)} items")
        
        with open('/tmp/cf_seed_cookies.json', 'w') as f:
            f.write(cookie_json)
        log("Cookies saved to /tmp/cf_seed_cookies.json")
        
        # Get localStorage
        storage = page.evaluate("() => JSON.stringify(localStorage)")
        with open('/tmp/cf_seed_storage.json', 'w') as f:
            f.write(storage)
        log("localStorage saved")
        
        # Get sessionStorage
        session = page.evaluate("() => JSON.stringify(sessionStorage)")
        with open('/tmp/cf_seed_session.json', 'w') as f:
            f.write(session)
        log("sessionStorage saved")
        
        page.screenshot(path='/tmp/cf_seed_dashboard.png')
        log("Dashboard screenshot!")
        
        # Now stay on page and try to find API tokens link
        log("Looking for profile/API navigation...")
        
        # Try clicking anywhere that might be the user menu
        # Look for header or user dropdown
        header = page.query_selector('header') or page.query_selector('nav')
        if header:
            links = header.query_selector_all('a, button')
            log(f"Header links: {len(links)}")
            for link in links[:10]:
                text = link.inner_text()[:40].strip()
                href = link.get_attribute('href') or ''
                log(f"  {text} -> {href}")
        
        # Try getting page HTML
        html = page.content()
        import re
        # Find any links to profile
        profile_links = re.findall(r'href=["\']([^"\']*profile[^"\']*)["\']', html, re.I)
        api_links = re.findall(r'href=["\']([^"\']*api[^"\']*)["\']', html, re.I)
        log(f"Profile links: {profile_links[:5]}")
        log(f"API links: {api_links[:5]}")
        
        # Get Redux state for user info
        redux = page.evaluate("() => localStorage.getItem('persist:cf-redux-store')")
        if redux:
            log(f"Redux store (first 300): {redux[:300]}")
        
        ctx.close()
    else:
        log(f"SIGNUP FAILED or CAPTCHA: {body[:300]}")
        page.screenshot(path='/tmp/cf_seed_fail.png')
    
    browser.close()