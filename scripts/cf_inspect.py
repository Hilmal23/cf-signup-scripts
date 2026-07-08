#!/usr/bin/env python3
from camoufox import Camoufox
import time

with Camoufox(headless=True, humanize=True, geoip=True) as browser:
    ctx = browser.new_context(locale='en-US')
    page = ctx.new_page()
    page.goto('https://dash.cloudflare.com/sign-up', wait_until='domcontentloaded', timeout=60000)
    time.sleep(5)
    
    url = page.url
    title = page.title()
    print(f"URL: {url}")
    print(f"Title: {title}")
    
    # Check for iframes
    frames = page.frames
    print(f"Number of frames: {len(frames)}")
    for i, f in enumerate(frames):
        print(f"  Frame {i}: {f.url[:80] if f.url else 'about:blank'}")
    
    # Check for shadow DOM
    shadow = page.evaluate('''() => {
        const host = document.querySelector('cloudflare-signup-app');
        if (host && host.shadowRoot) return "shadow DOM found";
        const iframe = document.querySelector('iframe');
        if (iframe) return "iframe found: " + iframe.src;
        const sections = document.querySelectorAll("section, div");
        return "total divs: " + sections.length;
    }''')
    print(f"Shadow/iframe check: {shadow}")
    
    # Get all inputs
    inputs = page.query_selector_all('input')
    print(f"Total inputs: {len(inputs)}")
    for inp in inputs:
        try:
            t = inp.get_attribute('type')
            i = inp.get_attribute('id')
            p = inp.get_attribute('placeholder')
            print(f"  Input: type={t} id={i} placeholder={p}")
        except:
            pass
    
    # Try to get body content from main frame
    body_text = frames[0].inner_text() if frames else page.inner_text('body')
    print(f"Main frame text: {body_text[:500]}")