#!/usr/bin/env python3
"""CF Signup with 2Captcha Turnstile solver"""
from camoufox import Camoufox
import time, re, random, json, sys
import subprocess

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

def solve_2captcha(sitekey, pageurl):
    """Solve via 2captcha.com (HTTP API)"""
    try:
        # Submit task
        cmd = [
            'curl', '-s', 'https://2captcha.com/in.php',
            '-d', f'key={TWOCAPTCHA_KEY}&method=turnstile&sitekey={sitekey}&pageurl={pageurl}&json=1'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        data = json.loads(result.stdout)
        if data['status'] != 1:
            log("2CAP ERROR submit: %s" % data)
            return None
        task_id = data['request']
        log("2CAP task: %s" % task_id)
        
        # Poll result
        for i in range(40):
            time.sleep(5)
            cmd2 = [
                'curl', '-s', 'https://2captcha.com/res.php',
                '-d', f'key={TWOCAPTCHA_KEY}&action=get&id={task_id}&json=1'
            ]
            result2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=15)
            data2 = json.loads(result2.stdout)
            if data2['status'] == 1:
                token = data2['request']
                log("2CAP token: %s..." % token[:30])
                return token
            if 'CAPCHA_NOT_READY' not in data2.get('request', ''):
                log("2CAP poll error: %s" % data2)
                break
        return None
    except Exception as e:
        log("2CAP exception: %s" % e)
        return None

def main():
    with open(LOG_FILE, 'w') as f: f.write('')
    email = rand_email()
    password = "CfTest!@#123456"
    log("Email: %s" % email)
    
    # Sitekey extracted from CF challenge URL - full key
    SITEKEY = '0x4AAAAAAABlg1iaAR3mgkjp'  # from cf-chl-widget iframe URL
    PAGEURL = 'https://dash.cloudflare.com/sign-up'
    
    log("Solving Turnstile via 2Captcha...")
    token = solve_2captcha(SITEKEY, PAGEURL)
    if not token:
        log("FAILED: 2Captcha token solve")
        sys.exit(1)
    
    log("Token obtained! Starting Camoufox...")
    
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
        time.sleep(3)
        
        if 'security' in page.content().lower():
            log("Challenge page - waiting 60s for Camoufox to resolve...")
            page.wait_for_timeout(60000)
        
        frame0 = page.frames[0]
        
        # Wait for form
        for _ in range(20):
            try:
                frame0.locator('input[name="email"]').wait_for(state='visible', timeout=3000)
                log("Form ready")
                break
            except:
                time.sleep(3)
        else:
            log("FORM TIMEOUT!")
            sys.exit(1)
        
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
        
        # Inject 2Captcha token into hidden input BEFORE submit
        log("Injecting token...")
        injected = page.evaluate('''() => {
            const inputs = document.querySelectorAll('input[type="hidden"]');
            for (const inp of inputs) {
                if (inp.name === 'cf-turnstile-response' || inp.id.includes('cf-chl-widget')) {
                    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(inp, arguments[0]);
                    inp.dispatchEvent(new Event('input', {bubbles: true}));
                    inp.dispatchEvent(new Event('change', {bubbles: true}));
                    return 'injected into ' + inp.id;
                }
            }
            return 'not found';
        }''', token)
        log("Inject result: %s" % injected)
        
        time.sleep(2)
        
        # Try postMessage to Turnstile iframe too
        try:
            page.evaluate('''() => {
                const frames = document.querySelectorAll('iframe');
                frames.forEach(f => {
                    if (f.src.includes('turnstile') || f.src.includes('challenge')) {
                        f.contentWindow.postMessage({
                            source: 'cf-turnstile',
                            response: arguments[0],
                            isFinal: true
                        }, '*');
                    }
                });
            }''', token)
            log("postMessage sent")
        except Exception as e:
            log("postMessage error: %s" % e)
        
        time.sleep(2)
        
        log("Submitting...")
        frame0.get_by_text("Sign up").last.click()
        time.sleep(8)
        
        # Check result
        body = frame0.inner_text('body')
        log("Result: %s" % body[:200].replace('\n', ' | '))
        
        if 'verify' in body.lower() or 'check your' in body.lower() or 'dashboard' in page.url():
            log("SUCCESS!")
            with open('/tmp/accounts_new.txt', 'a') as f:
                f.write("%s:%s\n" % (email, password))
        elif 'human' in body.lower() or 'security' in body.lower():
            log("CAPTCHA STILL BLOCKING")
        else:
            log("Unknown state: %s" % body[:100])
    
    log("=== DONE ===")

if __name__ == '__main__':
    main()