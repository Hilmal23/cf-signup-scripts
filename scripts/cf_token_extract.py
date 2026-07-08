#!/usr/bin/env python3
"""Extract API token via CF API after signup"""
from camoufox import Camoufox
import time, json

CF_PAGE = "https://dash.cloudflare.com/sign-up"

def extract_token():
    with Camoufox(headless=True, humanize=True, geoip=False) as browser:
        ctx = browser.new_context()
        page = ctx.new_page()
        
        # Signup with test account
        email = f"test{time.time()}@hilmal.store"
        pw = "TestPass123!"
        
        page.goto(CF_PAGE, timeout=45000)
        time.sleep(4)
        
        page.fill('input[name="email"]', email)
        page.fill('input[name="password"]', pw)
        page.click('button[type="submit"]')
        time.sleep(5)
        
        log(f"URL after signup: {page.url}")
        log(f"Title: {page.title()}")
        
        # Try clicking user profile menu
        try:
            # Click user avatar/menu
            page.click('[aria-label="User menu"], [data-testid="user-menu"], .user-menu, [class*="avatar"], [class*="profile"]')
            time.sleep(2)
            log(f"After user menu click: {page.url}")
        except Exception as e:
            log(f"User menu click failed: {e}")
        
        # Try getting cookies
        cookies = ctx.cookies()
        log(f"Cookies ({len(cookies)}):")
        for c in cookies:
            if 'cloudflare' in c['domain'].lower():
                log(f"  {c['name']}={c['value'][:30]}...")
        
        # Try clicking "My Profile" or similar
        try:
            profile_link = page.query_selector('a[href*="profile"], [href*="account"]')
            if profile_link:
                profile_link.click()
                time.sleep(3)
                log(f"Profile page: {page.url}")
        except Exception as e:
            log(f"Profile nav failed: {e}")
        
        # Try API directly from browser context
        try:
            api_response = page.evaluate("""
                async () => {
                    try {
                        const r = await fetch('https://api.cloudflare.com/client/v4/user', {
                            credentials: 'include',
                            headers: {'Authorization': 'Bearer undefined'}
                        });
                        return await r.text();
                    } catch(e) {
                        return 'ERROR: ' + e.message;
                    }
                }
            """)
            log(f"API response: {api_response[:200]}")
        except Exception as e:
            log(f"API eval failed: {e}")
        
        # Try localStorage
        try:
            storage = page.evaluate("() => JSON.stringify({...localStorage, ...sessionStorage})")
            log(f"Storage keys: {storage[:300]}")
        except:
            pass
        
        # Screenshot at current state
        page.screenshot(path='/tmp/cf_state.png', full_page=True)
        log("Screenshot saved!")
        
        # Get full page content
        body = page.inner_text('body')
        log(f"Body: {body[:500]}")
        
        # Look for any API token-like strings
        import re
        all_text = page.content()
        tokens = re.findall(r'[a-zA-Z0-9_-]{30,}', all_text)
        log(f"Long tokens found: {len(tokens)}")
        for t in tokens[:5]:
            log(f"  {t[:40]}...")
        
        browser.close()

def log(msg):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

if __name__ == "__main__":
    extract_token()