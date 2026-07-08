#!/usr/bin/env python3
"""Extract CF sitekey from custom CAPTCHA challenge"""
from camoufox import Camoufox
import time, re

with Camoufox(headless=True, humanize=True, geoip=False) as browser:
    ctx = browser.new_context(locale='en-US', viewport={'width': 1280, 'height': 720})
    ctx.clear_cookies()
    page = ctx.new_page()
    
    page.goto('https://dash.cloudflare.com/sign-up', wait_until='networkidle', timeout=60000)
    time.sleep(3)
    
    # Fill form to trigger CAPTCHA
    frame0 = page.frames[0]
    email = f"cf_debug_{time.time()}@web-library.net"
    try:
        frame0.locator('input[name="email"]').fill(email, timeout=5000)
        frame0.locator('input[type="password"]').fill("TestPass123!@#", timeout=5000)
        try:
            frame0.locator('input[name="ot-group-id-C0003"]').check(timeout=2000)
        except:
            pass
        frame0.get_by_text("Sign up").last.click()
    except Exception as e:
        print(f"Fill error: {e}")
    
    time.sleep(5)
    
    print("=== PAGE SOURCE (searching for sitekey) ===")
    content = page.content()
    
    # Search for sitekey patterns
    patterns = [
        r'data-sitekey="([^"]+)"',
        r'sitekey["\s:]+["\']([^"\']+)["\']',
        r'0x[a-f0-9A-F]{16,}',
        r'challenge[_-]?api',
        r'cf[_-]?chl',
    ]
    
    for pat in patterns:
        matches = re.findall(pat, content)
        if matches:
            print(f"Pattern '{pat}': {matches[:5]}")
    
    # Check hidden inputs
    print("\n=== HIDDEN INPUTS ===")
    hidden = page.query_selector_all('input[type="hidden"]')
    for inp in hidden:
        name = inp.get_attribute('name')
        id_ = inp.get_attribute('id')
        val = inp.get_attribute('value')
        if name and 'cf' in name.lower():
            print(f"  name={name}, id={id_}, value={val[:50] if val else 'empty'}")
    
    # Check for turnstile widgets
    print("\n=== CF TURNSTILE ELEMENTS ===")
    elements = page.query_selector_all('[class*="turnstile"], [id*="turnstile"], .cf-turnstile')
    for el in elements:
        print(f"  tag={el.tag_name}, class={el.get_attribute('class')}, id={el.get_attribute('id')}")
    
    # Check all script tags for challenge API
    print("\n=== SCRIPT SRC WITH CHALLENGE ===")
    scripts = page.query_selector_all('script[src]')
    for s in scripts:
        src = s.get_attribute('src')
        if 'challenge' in src.lower() or 'turnstile' in src.lower():
            print(f"  {src}")
    
    # Check main frame URL
    print(f"\n=== FRAME URLs ===")
    for i, f in enumerate(page.frames):
        print(f"  [{i}] url={f.url[:100]}")
    
    # Full body text
    body = frame0.inner_text('body')
    print(f"\n=== BODY TEXT ===\n{body[:500]}")
    
    browser.close()