#!/usr/bin/env python3
"""Test Social Login (OAuth) - does it skip Turnstile?"""
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
        
        print(f'Title: {page.title()}')
        print(f'URL: {page.url}')
        
        # Check for Turnstile (human challenge)
        human = page.query_selector('span:has-text("Let us know you are human")')
        print(f'Turnstile visible: {human is not None}')
        
        # Check for OAuth buttons
        oauth_btns = []
        for txt in ['Continue with Google', 'Continue with Apple', 'Continue with GitHub']:
            btn = page.query_selector(f'button:has-text("{txt}")')
            if btn:
                oauth_btns.append((txt, btn.is_visible()))
                print(f'{txt}: visible={btn.is_visible()}')
        
        # Check for regular email/password inputs
        email_inp = page.query_selector('input[name="email"]')
        pw_inp = page.query_selector('input[name="password"]')
        print(f'Email input visible: {email_inp.is_visible() if email_inp else False}')
        print(f'Password input visible: {pw_inp.is_visible() if pw_inp else False}')
        
        if human:
            print('\nTurnstile challenge active - testing Google OAuth click...')
            google_btn = page.query_selector('button:has-text("Continue with Google")')
            if google_btn and google_btn.is_visible():
                google_btn.click()
                time.sleep(5)
                print(f'After Google click - Title: {page.title()}')
                print(f'After Google click - URL: {page.url[:80]}')
                
                # Check if we're on Google OAuth or still on CF
                if 'google' in page.url.lower() or 'accounts.google' in page.url.lower():
                    print('REDIRECTED TO GOOGLE OAuth!')
                    # Save cookies + screenshot
                    page.screenshot(path='/tmp/cf_google_oauth.png')
                    cookies = ctx.cookies()
                    print(f'Cookies captured: {len(cookies)}')
                else:
                    print('Still on CF - check for new challenge')
                    page.screenshot(path='/tmp/cf_after_google.png')
        
        browser.close()

if __name__ == '__main__':
    main()