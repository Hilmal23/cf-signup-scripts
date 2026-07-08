#!/usr/bin/env python3
"""CF signup - human-like interaction to pass behavioral challenge"""
from camoufox import Camoufox
import time, random

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

email = f"human{int(time.time())}@hilmal.store"
pw = "HumanTest123!"
log(f"Email: {email}")

with Camoufox(headless=True, geoip=False) as browser:
    ctx = browser.new_context(
        color_scheme='light',
        timezone_id='America/Chicago',
        locale='en-US',
    )
    page = ctx.new_page()
    
    # Set realistic viewport
    page.set_viewport_size({"width": 1280, "height": 800})
    
    page.goto("https://dash.cloudflare.com/sign-up", timeout=60000)
    time.sleep(2)
    
    # Mouse movement simulation to pass behavioral detection
    def human_move(x, y, duration=0.3):
        page.mouse.move(x, y)
        time.sleep(duration)
    
    # Move mouse around the page naturally
    page.mouse.move(400, 300)
    time.sleep(0.3)
    page.mouse.move(500, 350)
    time.sleep(0.2)
    
    # Focus on email field with mouse click (human-like)
    email_field = page.query_selector('input[name="email"]')
    if email_field:
        box = email_field.bounding_box()
        if box:
            # Move to field with human-like path
            page.mouse.move(int(box['x'] + box['width']/2), int(box['y'] - 20))
            time.sleep(0.2)
            page.mouse.move(int(box['x'] + box['width']/2), int(box['y'] + box['height']/2))
            time.sleep(0.1)
            
            # Type email with human timing
            email_field.click()
            time.sleep(0.5)
            
            for char in email:
                email_field.type(char, delay=random.uniform(0.05, 0.15))
                if random.random() < 0.05:
                    time.sleep(random.uniform(0.1, 0.3))
            time.sleep(random.uniform(0.3, 0.6))
    
    # Mouse move to password field
    pw_field = page.query_selector('input[name="password"]')
    if pw_field:
        box = pw_field.bounding_box()
        if box:
            page.mouse.move(int(box['x'] + box['width']/2), int(box['y'] - 20))
            time.sleep(0.2)
            page.mouse.move(int(box['x'] + box['width']/2), int(box['y'] + box['height']/2))
            time.sleep(0.1)
            
            pw_field.click()
            time.sleep(0.5)
            
            for char in pw:
                pw_field.type(char, delay=random.uniform(0.05, 0.12))
                if random.random() < 0.05:
                    time.sleep(random.uniform(0.1, 0.25))
            time.sleep(random.uniform(0.3, 0.5))
    
    # Random mouse movements while typing
    page.mouse.move(600, 400)
    time.sleep(0.2)
    page.mouse.move(700, 300)
    time.sleep(0.15)
    
    # Scroll down slightly (natural behavior)
    page.mouse.wheel(0, 200)
    time.sleep(0.5)
    
    # Check challenge state before submit
    challenge_val = page.evaluate("() => document.querySelector('input[name=\"cf_challenge_response\"]')?.value || 'empty'")
    log(f"Challenge response before submit: {challenge_val[:30]}")
    
    # Move mouse to submit button
    submit_btn = page.query_selector('button[type="submit"]')
    if submit_btn:
        box = submit_btn.bounding_box()
        if box:
            page.mouse.move(int(box['x'] + box['width']/2), int(box['y'] + box['height']/2))
            time.sleep(0.3)
            page.mouse.click(int(box['x'] + box['width']/2), int(box['y'] + box['height']/2))
            log("Clicked submit button")
    
    # Wait for response
    time.sleep(10)
    
    title = page.title()
    url = page.url
    body = page.inner_text('body')
    
    log(f"Result: {title} | {url}")
    
    if 'dashboard' in title.lower() and 'sign-up' not in url:
        log("SUCCESS! Account created!")
    elif 'let us know' in body.lower():
        log("CAPTCHA challenge shown - waiting...")
        # Wait additional time for challenge
        time.sleep(30)
        title2 = page.title()
        url2 = page.url
        body2 = page.inner_text('body')
        log(f"After wait: {title2} | {url2}")
        if 'dashboard' in title2.lower() and 'sign-up' not in url2:
            log("SUCCESS after wait!")
        else:
            log(f"Still challenged: {body2[:200]}")
    elif 'unable to sign up' in body.lower():
        log("BLOCKED: Unable to sign up")
    else:
        log(f"Other result: {body[:200]}")
    
    page.screenshot(path='/tmp/cf_human.png')
    log("Screenshot saved!")
    browser.close()

log("=== Done ===")