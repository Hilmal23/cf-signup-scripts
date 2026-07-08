#!/usr/bin/env python3
"""Test OAuth signup: Does it create CF account WITHOUT any challenge?"""
from playwright.sync_api import sync_playwright
import time

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            executable_path='/snap/chromium/3483/usr/lib/chromium-browser/chrome',
            args=['--no-sandbox', '--disable-setuid-sandbox', '--ignore-certificate-errors',
                  '--allow-running-insecure-content', '--ignore-certificate-errors-spki-list=*']
        )
        ctx = browser.new_context(
            proxy={'server': 'http://brd.superproxy.io:33335',
                   'username': 'brd-customer-hl_c0f6789c-zone-web_unlocker1',
                   'password': 'ds3ovbwhs69y'}
        )
        page = ctx.new_page()
        page.goto('https://dash.cloudflare.com/sign-up', timeout=60000)
        time.sleep(10)
        
        print(f'Page: {page.title()}')
        
        # Get all cookies after page load
        init_cookies = len(ctx.cookies())
        print(f'Init cookies: {init_cookies}')
        
        # Click Google OAuth
        google_btn = page.query_selector('button:has-text("Continue with Google")')
        if google_btn and google_btn.is_visible():
            print('Clicking Google OAuth...')
            google_btn.click()
            time.sleep(8)
        
        print(f'\nAfter OAuth - Title: {page.title()}')
        print(f'After OAuth - URL: {page.url[:80]}')
        
        # Check URL - is it Google login or CF dashboard?
        page.screenshot(path='/tmp/cf_oauth_result.png')
        
        # If URL contains 'google' or 'oidc' — we're in OAuth flow
        url_lower = page.url.lower()
        if 'google' in url_lower or 'oidc.iam' in url_lower or 'accounts.google' in url_lower:
            print('IN OAUTH FLOW - Google login page detected')
            
            # Check if we can login with Google credentials
            # Try to see what Google login page looks like
            email_inp = page.query_selector('input[type="email"], input[name="identifier"]')
            if email_inp:
                print(f'Google email input visible: {email_inp.is_visible()}')
                print('Need Google credentials to proceed!')
            
            # Try "Sign in" button vs "Create account" 
            for btn_txt in ['Sign in', 'Next', 'Create account', 'Next']:
                btn = page.query_selector(f'button:has-text("{btn_txt}")')
                if btn:
                    print(f'Button found: {btn_txt} visible={btn.is_visible()}')
        
        elif 'dashboard' in url_lower or 'verify' in url_lower:
            print('CF ACCOUNT CREATED! (in dashboard or verify page)')
        
        # Save cookies
        final_cookies = ctx.cookies()
        print(f'\nFinal cookies: {len(final_cookies)}')
        for c in final_cookies:
            print(f'  {c["name"]}: {c["value"][:20]}...')
        
        browser.close()
        print('\nDone!')

if __name__ == '__main__':
    main()