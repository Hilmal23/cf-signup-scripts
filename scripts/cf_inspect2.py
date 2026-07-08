#!/usr/bin/env python3
from camoufox import Camoufox
import time

LOG_FILE = '/tmp/cf_camoufox.log'
def log(msg):
    ts = time.strftime('%H:%M:%S')
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')

with open(LOG_FILE, 'w') as f:
    f.write('')

log("Starting Camoufox...")
with Camoufox(headless=True, humanize=True, geoip=True) as browser:
    ctx = browser.new_context(locale='en-US', viewport={'width': 1280, 'height': 720})
    # Clear ALL cookies/storage
    ctx.clear_cookies()
    
    page = ctx.new_page()
    log("Navigating to CF signup...")
    page.goto('https://dash.cloudflare.com/sign-up', wait_until='networkidle', timeout=60000)
    time.sleep(3)
    
    url = page.url
    title = page.title()
    log(f"URL: {url}")
    log(f"Title: {title}")
    
    # Check for iframes
    frames = page.frames
    log(f"Number of frames: {len(frames)}")
    for i, f in enumerate(frames):
        log(f"  Frame {i}: {f.url[:100] if f.url else 'about:blank'}")
    
    # Get text from all frames
    for i, f in enumerate(frames):
        try:
            text = f.inner_text('body')
            if text.strip():
                log(f"  Frame {i} text: {text[:300].replace(chr(10), ' | ')}")
        except:
            pass
    
    # Check for signup form
    inputs = page.query_selector_all('input')
    log(f"Total inputs: {len(inputs)}")
    for inp in inputs:
        try:
            t = inp.get_attribute('type')
            i = inp.get_attribute('id')
            p = inp.get_attribute('placeholder')
            v = inp.get_attribute('value')
            if t and t != 'hidden':
                log(f"  Input: type={t} id={i} placeholder={p} value={v[:20] if v else ''}")
        except:
            pass
    
    # Check for email input specifically
    email_inputs = page.query_selector_all('input[type="email"]')
    log(f"Email inputs: {len(email_inputs)}")
    
    # Check for submit buttons
    buttons = page.query_selector_all('button')
    log(f"Buttons: {len(buttons)}")
    for btn in buttons:
        try:
            t = btn.inner_text()
            if t.strip():
                log(f"  Button: {t.strip()[:50]}")
        except:
            pass
    
    log("Done!")