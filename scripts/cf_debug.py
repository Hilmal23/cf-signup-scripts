#!/usr/bin/env python3
from camoufox import Camoufox
import time, json, sys

LOG_FILE = '/tmp/cf_camoufox.log'

def log(msg):
    ts = time.strftime('%H:%M:%S')
    line = "[%s] %s" % (ts, msg)
    print(line)
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')

with open(LOG_FILE, 'w') as f:
    f.write('')

with Camoufox(headless=True, humanize=True, geoip=True) as browser:
    ctx = browser.new_context(locale='en-US', viewport={'width': 1280, 'height': 720})
    ctx.clear_cookies()
    page = ctx.new_page()
    page.goto('https://dash.cloudflare.com/sign-up', wait_until='networkidle', timeout=60000)
    time.sleep(3)
    if 'security' in page.content().lower():
        log("Waiting initial challenge...")
        page.wait_for_timeout(60000)
    
    frame0 = page.frames[0]
    
    for _ in range(20):
        try:
            frame0.locator('input[name="email"]').wait_for(state='visible', timeout=3000)
            log("Form ready")
            break
        except:
            log("Waiting form...")
            time.sleep(3)
    else:
        log("Form never appeared!")
        page.screenshot(path='/tmp/cf_debug.png')
        log("Debug screenshot saved")
        sys.exit(1)
    
    frame0.locator('input[name="email"]').fill('cf111111111111@web-library.net', timeout=10000)
    frame0.locator('input[type="password"]').fill('CfTest!@#123456', timeout=10000)
    try:
        frame0.locator('input[type="checkbox"]').last.check(timeout=2000)
    except Exception as e:
        log("Checkbox: " + str(e))
    frame0.get_by_text("Sign up").last.click()
    time.sleep(3)
    
    page.screenshot(path='/tmp/cf_debug.png')
    log("Screenshot saved: /tmp/cf_debug.png")
    
    debug = frame0.evaluate('''() => {
        var visible = [];
        document.querySelectorAll("*").forEach(function(el) {
            if (el.offsetParent === null) return;
            var style = window.getComputedStyle(el);
            if (style.display === "none" || style.visibility === "hidden") return;
            var rect = el.getBoundingClientRect();
            if (rect.width < 5 || rect.height < 5) return;
            var text = (el.innerText || el.textContent || "").trim();
            if (text && text.length > 1) {
                visible.push({
                    tag: el.tagName,
                    cls: el.className.slice(0, 60),
                    text: text.slice(0, 120),
                    x: Math.round(rect.x),
                    y: Math.round(rect.y),
                    w: Math.round(rect.width),
                    h: Math.round(rect.height)
                });
            }
        });
        return JSON.stringify(visible);
    }''')
    
    log("Visible elements:")
    data = json.loads(debug)
    data_sorted = sorted(data, key=lambda x: x['y'])
    for el in data_sorted:
        if len(el['text']) > 2:
            log("  [%4d,%4d] %s(%s): \"%s\"" % (el['x'], el['y'], el['tag'], el['cls'][:40], el['text'][:80]))
    
    log("Done!")