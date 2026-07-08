#!/usr/bin/env python3
"""Test CF signup - try without humanize"""
from camoufox import Camoufox
import time, random

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

# Try 3 variations
configs = [
    {"headless": True, "geoip": False},  # no humanize
    {"headless": True, "geoip": False, "fingerprint": "randomize"},  # random fingerprint
    {"headless": False, "geoip": False},  # visible
]

for i, config in enumerate(configs):
    log(f"=== Test {i+1}: {config} ===")
    email = f"test{i}{int(time.time())}@hilmal.store"
    pw = "TestPass123!"
    
    try:
        with Camoufox(**config) as browser:
            ctx = browser.new_context()
            page = ctx.new_page()
            
            page.goto("https://dash.cloudflare.com/sign-up", timeout=45000)
            time.sleep(5)
            
            log(f"Page title: {page.title()}")
            
            # Fill form
            page.fill('input[name="email"]', email)
            time.sleep(random.uniform(0.3, 0.8))
            page.fill('input[name="password"]', pw)
            time.sleep(random.uniform(0.3, 0.8))
            
            # Submit
            page.click('button[type="submit"]')
            time.sleep(8)
            
            log(f"After submit: {page.title()} | {page.url}")
            body = page.inner_text('body')[:300]
            log(f"Body: {body}")
            
            # Check for errors
            if 'unable to sign up' in body or 'human' in body:
                log("BLOCKED by CF!")
            
            page.screenshot(path=f'/tmp/cf_test_{i+1}.png')
            ctx.close()
            browser.close()
            
    except Exception as e:
        log(f"Error: {e}")
    
    time.sleep(3)