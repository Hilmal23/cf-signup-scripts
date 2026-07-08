#!/usr/bin/env python3
"""CF Signup - 2Captcha + smart challenge wait"""
from camoufox import Camoufox
import time, re, random, json, sys, subprocess

LOG_FILE = '/tmp/cf_2cap.log'
TWOCAPTCHA_KEY = '3da28555894fd89bb569b748731e9400'

def log(msg):
    ts = time.strftime('%H:%M:%S')
    line = "[%s] %s" % (ts, msg)
    print(line)
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')

def rand_email():
    return "cf%s@web-library.net" % (''.join(random.choices('0123456789', k=12)))

def get_sitekey(page):
    for f in page.frames:
        m = re.search(r'0x[a-f0-9A-F]{16,}', f.url)
        if m:
            return m.group(0)
    return None

def solve_2captcha(sitekey, pageurl, max_wait=120):
    try:
        url = 'https://2captcha.com/in.php?key=%s&method=turnstile&sitekey=%s&pageurl=%s&json=1' % (TWOCAPTCHA_KEY, sitekey, pageurl)
        r = subprocess.run(['curl', '-s', url], capture_output=True, text=True, timeout=15)
        data = json.loads(r.stdout)
        if data['status'] != 1:
            log("Submit error: %s" % data)
            return None
        tid = data['request']
        log("Task: %s" % tid)
        
        for i in range(max_wait // 5):
            time.sleep(5)
            r2 = subprocess.run(['curl', '-s', 'https://2captcha.com/res.php?key=%s&action=get&id=%s&json=1' % (TWOCAPTCHA_KEY, tid)],
                              capture_output=True, text=True, timeout=15)
            d2 = json.loads(r2.stdout)
            if d2['status'] == 1:
                log("Token: %s..." % d2['request'][:30])
                return d2['request']
            if 'CAPCHA_NOT_READY' not in d2.get('request', ''):
                log("Poll: %s" % d2)
                break
        return None
    except Exception as e:
        log("2CAP err: %s" % e)
        return None

def main():
    with open(LOG_FILE, 'w') as f: f.write('')
    email = rand_email()
    password = "CfTest!@#123456"
    PAGEURL = 'https://dash.cloudflare.com/sign-up'
    log("Email: %s" % email)
    
    with Camoufox(headless=True, humanize=True, geoip=False) as browser:
        ctx = browser.new_context(locale='en-US', viewport={'width': 1280, 'height': 720})
        ctx.clear_cookies()
        
        page = ctx.new_page()
        
        # Try networkidle first (fast path if challenge resolves quickly)
        log("1. Navigate (load with short timeout)...")
        try:
            page.goto(PAGEURL, wait_until='load', timeout=15000)
            time.sleep(5)
        except:
            log("load timeout (expected - challenge blocking)")
            time.sleep(5)
        
        title = page.title()
        log("Title: %s" % title)
        
        if 'Just a moment' in title:
            log("Challenge showing - waiting for Camoufox to resolve...")
            for i in range(50):
                time.sleep(3)
                title = page.title()
                if 'Just a moment' not in title:
                    log("Resolved at %ds" % ((i+1)*3))
                    break
                if i % 5 == 0:
                    log("  waiting... %ds" % ((i+1)*3))
            else:
                log("BOT TIMEOUT!")
                sys.exit(1)
        
        time.sleep(3)  # Let form render
        
        frame0 = page.frames[0]
        
        # Wait for form inputs
        for i in range(30):
            inputs = frame0.query_selector_all('input[name="email"]')
            if inputs:
                log("Form ready after %ds" % (i*2))
                break
            time.sleep(2)
        else:
            log("FORM not found. Dumping inputs...")
            all_i = frame0.query_selector_all('input')
            log("Total inputs: %d" % len(all_i))
            for inp in all_i[:5]:
                log("  %s / %s" % (inp.get_attribute('name'), inp.get_attribute('type')))
            sys.exit(1)
        
        # Extract sitekey from Turnstile iframe
        sitekey = get_sitekey(page)
        if not sitekey:
            log("No sitekey - trying alternative...")
            sitekey = '0x4AAAAAAAJel0iaAR3mgkjp'  # CF standard sitekey
        
        log("2. Sitekey: %s" % sitekey)
        
        # Solve Turnstile via 2Captcha
        log("3. Solving Turnstile via 2Captcha...")
        token = solve_2captcha(sitekey, PAGEURL)
        if not token:
            log("Solve FAILED - retry once...")
            time.sleep(5)
            token = solve_2captcha(sitekey, PAGEURL)
            if not token:
                log("Solve FAILED twice")
                sys.exit(1)
        
        # Inject token into hidden input
        log("4. Injecting token...")
        injected = frame0.evaluate('''(tok) => {
            const inp = document.querySelector('input[name="cf-turnstile-response"]')
                     || document.querySelector('#cf-chl-widget-jnghj_response')
                     || document.querySelector('input[type="hidden"][id*="cf-chl"]');
            if (inp) {
                Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(inp, tok);
                inp.dispatchEvent(new Event('input',{bubbles:true}));
                inp.dispatchEvent(new Event('change',{bubbles:true}));
                return inp.id || 'injected';
            }
            return 'not found: '+document.querySelectorAll('input[type="hidden"]').length+' hidden inputs';
        }''', token)
        log("Inject: %s" % injected)
        time.sleep(3)
        
        # Fill form
        log("5. Filling form...")
        try:
            frame0.locator('input[name="email"]').fill(email, timeout=10000)
            time.sleep(random.uniform(0.5, 1.2))
            frame0.locator('input[type="password"]').fill(password, timeout=10000)
        except Exception as e:
            log("Fill error: %s" % e)
            sys.exit(1)
        
        try:
            frame0.locator('input[name="ot-group-id-C0003"]').check(timeout=3000)
            log("Terms checked")
        except:
            try:
                frame0.locator('input[type="checkbox"]').last.check(timeout=2000)
                log("Checkbox checked")
            except:
                log("Terms skipped")
        
        time.sleep(random.uniform(1.0, 2.0))
        
        # Re-inject token before submit
        frame0.evaluate('''(tok) => {
            const inp = document.querySelector('input[name="cf-turnstile-response"]')
                     || document.querySelector('input[type="hidden"][id*="cf-chl"]');
            if (inp) {
                Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(inp, tok);
                inp.dispatchEvent(new Event('input',{bubbles:true}));
            }
        }''', token)
        time.sleep(1)
        
        log("6. Submitting...")
        frame0.get_by_text("Sign up").last.click()
        time.sleep(10)
        
        body = frame0.inner_text('body')
        url = page.url
        log("URL: %s" % url)
        log("Body: %s" % body[:400].replace('\n', ' | '))
        
        if 'verify' in body.lower() or 'check your' in body.lower() or 'dashboard' in url:
            log("🎉 SUCCESS!")
            with open('/tmp/accounts_new.txt', 'a') as f:
                f.write("%s:%s\n" % (email, password))
        elif 'human' in body.lower() or 'attention' in body.lower():
            log("⚠️ CAPTCHA blocking after submit")
        else:
            log("State: %s" % body[:100])
        
        log("=== DONE ===")

if __name__ == '__main__':
    main()