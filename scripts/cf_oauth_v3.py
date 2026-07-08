#!/usr/bin/env python3
"""
CF Signup - OAUTH with REAL Google accounts
Strategy: Use existing Google accounts OR create new ones via Spacemail
"""
from playwright.sync_api import sync_playwright
import time, random

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

CHROMIUM = "/snap/chromium/current/usr/lib/chromium-browser/chrome"
PROXY_USER = "brd-customer-hl_c0f6789c-zone-web_unlocker1"
PROXY_PASS = "ds3ovbwhs69y"
PROXY = {'server': 'http://brd.superproxy.io:33335', 'username': PROXY_USER, 'password': PROXY_PASS}
CHROME_ARGS = ["--no-sandbox","--disable-setuid-sandbox","--ignore-certificate-errors","--allow-running-insecure-content"]

def oauth_signup(google_email, google_pw):
    """Sign up for CF using Google OAuth"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=CHROMIUM, args=CHROME_ARGS)
        ctx = browser.new_context(proxy=PROXY)
        page = ctx.new_page()
        
        # Step 1: CF signup page
        page.goto("https://dash.cloudflare.com/sign-up", timeout=60000)
        time.sleep(8)
        
        for _ in range(3):
            try:
                allow = page.query_selector('button:has-text("Allow All")')
                if allow and allow.is_visible():
                    allow.click()
                    time.sleep(1)
                    break
            except:
                pass
            time.sleep(1)
        
        # Step 2: Click Continue with Google
        google_btn = page.query_selector('button:has-text("Google")')
        if not google_btn or not google_btn.is_visible():
            log("No Google button!")
            browser.close()
            return None
        
        google_btn.click()
        time.sleep(4)
        
        log(f"OAuth URL: {page.url}")
        
        # Step 3: Fill Google email
        for attempt in range(10):
            email_inp = page.query_selector('input[type="email"], input[name="identifier"], input#identifier')
            if email_inp and email_inp.is_visible():
                email_inp.fill(google_email)
                time.sleep(0.3)
                page.keyboard.press('Enter')
                log(f"Filled: {google_email}")
                break
            time.sleep(1)
        else:
            log("No Google email input!")
            page.screenshot(path='/tmp/oauth_no_email_in.png')
            browser.close()
            return None
        
        # Step 4: Wait for password or error
        time.sleep(3)
        log(f"After email: {page.url} | {page.title()}")
        
        # Check for Google account error
        body = page.inner_text('body')
        if 'couldn\'t find' in body.lower() or 'not a valid google' in body.lower() or 'no account' in body.lower():
            log(f"Google account not found: {body[:200]}")
            page.screenshot(path='/tmp/oauth_no_google.png')
            browser.close()
            return "ACCOUNT_NOT_EXIST"
        
        # Step 5: Fill password
        for i in range(15):
            pw_inp = page.query_selector('input[type="password"], input[name="password"], input#password')
            if pw_inp and pw_inp.is_visible():
                pw_inp.fill(google_pw)
                time.sleep(0.3)
                page.keyboard.press('Enter')
                log(f"Filled password for {google_email}")
                break
            time.sleep(1)
        else:
            log("No password field appeared!")
            page.screenshot(path='/tmp/oauth_no_pw2.png')
            browser.close()
            return None
        
        # Step 6: Wait for CF dashboard redirect
        for i in range(20):
            time.sleep(1)
            url = page.url
            
            if 'dashboard' in url.lower() and 'sign-up' not in url:
                log(f"===== DASHBOARD! ===== {url}")
                page.screenshot(path='/tmp/oauth_cf_success.png')
                
                # Get CF cookies for token extraction
                cookies = ctx.cookies()
                cf_auth = next((c['value'] for c in cookies if c['name'] == 'CF_Authorization'), None)
                log(f"CF_Authorization: {cf_auth[:50]}..." if cf_auth else "No CF_Auth cookie")
                
                browser.close()
                return google_email
            
            if 'sign-up' in url.lower() and 'oidc' not in url:
                body = page.inner_text('body')
                log(f"Back to signup: {body[:200]}")
                page.screenshot(path='/tmp/oauth_back_to_signup.png')
                browser.close()
                return None
            
            if i % 5 == 0:
                log(f"  [{i}s] {page.title()[:40]} | {url[:50]}")
        
        page.screenshot(path='/tmp/oauth_timeout.png')
        browser.close()
        return None

def create_google_account():
    """Create a new Google account using Spacemail"""
    import requests
    
    google_email = f"cf{int(time.time())}{random.randint(100,999)}@gmail.com"
    google_pw = "CfSignup123!"
    
    log(f"Creating Google account: {google_email}")
    
    # Try to create Google account via API (this might not work directly)
    # Google requires verification - we can't easily create accounts this way
    
    # Alternative: Use existing Google accounts we have
    # or create accounts via Google's account creation flow
    
    return None  # Can't create Google accounts without email verification

def main():
    log("=== CF Signup - OAUTH (REAL Google accounts) ===")
    
    # Try existing Google account first
    existing_accounts = [
        ("tengkeikmal@gmail.com", "Ikmal230104"),
        ("cfautomation01@gmail.com", "CfSignup123!"),
    ]
    
    for google_email, google_pw in existing_accounts:
        log(f"\nTrying: {google_email}")
        result = oauth_signup(google_email, google_pw)
        
        if result == "ACCOUNT_NOT_EXIST":
            log(f"Account doesn't exist, try next")
            continue
        elif result:
            log(f"===== OAUTH SUCCESS! =====")
            log(f"Google: {result}")
            break
        else:
            log(f"Failed, try next account")
    
    log("\nDone")

if __name__ == '__main__':
    main()