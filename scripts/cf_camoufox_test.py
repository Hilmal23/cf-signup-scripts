#!/usr/bin/env python3
"""CF Signup Test with Camoufox Python - FIXED"""
import sys, os, time

LOG_FILE = '/tmp/cf_camoufox.log'

def log(msg):
    ts = time.strftime('%H:%M:%S')
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')

def main():
    with open(LOG_FILE, 'w') as f:
        f.write('')
    
    try:
        from camoufox import Camoufox
    except ImportError:
        log("ERROR: camoufox not installed")
        sys.exit(1)
    
    log("Starting Camoufox...")
    
    try:
        with Camoufox(headless=True, humanize=True, geoip=True) as browser:
            log("Browser context ready")
            
            # Create context then page
            ctx = browser.new_context(locale='en-US')
            page = ctx.new_page()
            
            log("Navigating to CF signup...")
            page.goto('https://dash.cloudflare.com/sign-up', wait_until='domcontentloaded', timeout=60000)
            
            # Wait for page to load
            time.sleep(3)
            
            url = page.url
            title = page.title() if callable(page.title) else str(page.title)
            log(f"URL: {url}")
            log(f"Title: {title}")
            
            # Check for challenge
            if 'cdn-cgi' in url or title == 'Just a moment...':
                log("Challenge detected - waiting...")
                start = time.time()
                while 'cdn-cgi' in page.url or page.title() == 'Just a moment...':
                    if time.time() - start > 90:
                        log("Challenge TIMEOUT after 90s!")
                        break
                    time.sleep(3)
                time.sleep(2)
                url = page.url
                title = page.title() if callable(page.title) else str(page.title)
            
            log("=== RESULT ===")
            log(f"Final URL: {url}")
            log(f"Final Title: {title}")
            
            # Check for form elements
            try:
                email_input = page.query_selector('input[type="email"]')
                log(f"Has email input: {email_input is not None}")
                if email_input:
                    email_input.highlight()
                    log(f"Email input visible: {email_input.is_visible()}")
            except Exception as e:
                log(f"Email check error: {e}")
            
            # Get page HTML snippet
            try:
                html = page.content()
                if 'email' in html.lower() or 'sign up' in html.lower():
                    log("Page contains signup content!")
                else:
                    log("Page may be loading...")
                # Get visible text
                body = page.inner_text('body')
                log(f"Body text ({len(body)} chars): {body[:300].replace(chr(10), ' | ')}")
            except Exception as e:
                log(f"Content error: {e}")
            
            log("Done!")
    except Exception as e:
        log(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()