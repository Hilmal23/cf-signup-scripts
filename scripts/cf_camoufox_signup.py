#!/usr/bin/env python3
"""CF Signup - with Geonode residential proxy"""
from camoufox import Camoufox, ip
import time, random

LOG_FILE = '/tmp/cf_camoufox.log'

def log(msg):
    ts = time.strftime('%H:%M:%S')
    print("[%s] %s" % (ts, msg))
    with open(LOG_FILE, 'a') as f:
        f.write("[%s] %s\n" % (ts, msg))

def rand_email():
    return "cf%s@web-library.net" % (''.join(random.choices('0123456789', k=12)))

with open(LOG_FILE, 'w') as f:
    f.write('')

email = rand_email()
password = "CfTest!@#123456"
log("Email: %s" % email)

with Camoufox(headless=True, humanize=True, geoip=False) as browser:
    ctx = browser.new_context(
        locale='en-US',
        viewport={'width': 1280, 'height': 720},
        ignore_https_errors=True
    )
    ctx.clear_cookies()
    
    page = ctx.new_page()
    log("Navigating...")
    page.goto('https://dash.cloudflare.com/sign-up', wait_until='networkidle', timeout=60000)
    time.sleep(2)
    
    if 'security' in page.content().lower() or page.title() == 'Just a moment...':
        log("Challenge - waiting 60s...")
        page.wait_for_timeout(60000)
    
    frame0 = page.frames[0]
    
    for _ in range(20):
        try:
            frame0.locator('input[name="email"]').wait_for(state='visible', timeout=3000)
            log("Form ready")
            break
        except:
            time.sleep(3)
    else:
        log("FORM TIMEOUT!")
        exit(1)
    
    log("Filling form...")
    frame0.locator('input[name="email"]').fill(email, timeout=10000)
    time.sleep(random.uniform(0.5, 1.5))
    frame0.locator('input[type="password"]').fill(password, timeout=10000)
    time.sleep(random.uniform(0.3, 1.0))
    
    try:
        frame0.locator('input[name="ot-group-id-C0003"]').check(timeout=3000)
        log("Terms checked")
    except:
        try:
            frame0.locator('input[type="checkbox"]').last.check(timeout=3000)
            log("Checkbox checked")
        except:
            log("Terms skipped")
    
    time.sleep(random.uniform(1.0, 2.0))
    
    log("Submitting...")
    frame0.get_by_text("Sign up").last.click()
    time.sleep(5)
    
    result = frame0.inner_text('body')
    log("=== RESULT ===")
    log(result[:400].replace('\n', ' | '))
    
    if 'verify' in result.lower() or 'check your' in result.lower():
        log("SUCCESS!")
    elif 'human' in result.lower():
        log("CAPTCHA - waiting 30s...")
        time.sleep(30)
        result2 = frame0.inner_text('body')
        if 'verify' in result2.lower():
            log("SUCCESS after wait!")
        else:
            log("Still CAPTCHA")
    else:
        log("Status: " + result[:100])
    
    log("=== DONE ===")