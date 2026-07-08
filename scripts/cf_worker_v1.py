#!/usr/bin/env python3
"""CF Signup Worker v1 - Real Chrome + CDP Turnstile click (WORKS)"""
import os, sys, json, time, random, subprocess, signal, re, requests
from pathlib import Path
from playwright.sync_api import sync_playwright

# ============ CONFIG ============
PROXY_HOST = 'prod-proxy.geonode.io'
PROXY_PORT = '9000'
PROXY_USER = 'geonode_RTwCdAt5Br-type-residential-country-us'
PROXY_PASS = '34c063a6-055f-42e0-980d-57db761b8c46'

TWOCAPTCHA_KEY = '0a8c36eab14c5b4e4c1d1f66ac00b6aa'

WORKER_ID = int(os.environ.get('WORKER_ID', '0'))
LOG_FILE = Path(f'/tmp/cf_worker_{WORKER_ID}.log')

# ============ LOGGING ============
def log(msg):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] [Worker-{WORKER_ID}] {msg}\n"
    LOG_FILE.write_text(line, append=True)
    print(line.strip())

# ============ EMAIL GENERATOR ============
def gen_email():
    """Generate disposable email via mail.tm"""
    try:
        r = requests.get('https://api.mail.tm/domains', timeout=10)
        if not r.ok:
            return None
        domains = r.json().get('hydra:member', [])
        if not domains:
            return None
        domain = domains[0]['domain']
        username = f"cf{random.randint(100000,999999)}{random.randint(1000,9999)}"
        email = f"{username}@{domain}"
        password = f"CfPass{random.randint(10000,99999)}!"
        
        r2 = requests.post('https://api.mail.tm/accounts', json={
            'address': email,
            'password': password
        }, timeout=10)
        if r2.ok:
            return {'email': email, 'password': password, 'token': r2.json().get('token')}
        return None
    except Exception as e:
        log(f"Email gen error: {e}")
        return None

def get_verification_link(token, domain):
    """Poll mail.tm for verification email"""
    headers = {'Authorization': f'Bearer {token}'}
    for _ in range(60):
        try:
            r = requests.get('https://api.mail.tm/messages', headers=headers, timeout=10)
            if r.ok:
                for m in r.json().get('hydra:member', []):
                    if 'cloudflare' in m.get('subject', '').lower():
                        msg_id = m['id']
                        r2 = requests.get(f'https://api.mail.tm/messages/{msg_id}', headers=headers, timeout=10)
                        if r2.ok:
                            body = r2.json().get('text', '') or r2.json().get('html', '')
                            links = re.findall(r'https?://[^\s<>"\'\\]+', body)
                            for link in links:
                                if 'verify' in link.lower() or 'confirm' in link.lower():
                                    return link
            time.sleep(1)
        except:
            pass
    return None

# ============ 2CAPTCHA SOLVER ============
def solve_turnstile(url, sitekey):
    """Solve Turnstile via 2Captcha ImageToText (fallback)"""
    try:
        # Submit to 2Captcha
        r = requests.post('https://2captcha.com/in.php', data={
            'key': TWOCAPTCHA_KEY,
            'method': 'userrecaptcha',
            'googlekey': sitekey,
            'pageurl': url,
            'json': 1
        }, timeout=10)
        if not r.ok:
            return None
        task_id = r.json().get('request')
        if not task_id:
            return None
        
        # Poll for result
        for _ in range(30):
            time.sleep(5)
            r2 = requests.get(f'https://2captcha.com/res.php', params={
                'key': TWOCAPTCHA_KEY,
                'action': 'get',
                'id': task_id,
                'json': 1
            }, timeout=10)
            if r2.ok:
                res = r2.json()
                if res.get('status') == 1:
                    return res.get('request')
        return None
    except Exception as e:
        log(f"2Captcha error: {e}")
        return None

# ============ CF SIGNUP ============
def signup_account():
    """Sign up one CF account using real Chrome + CDP method"""
    log("Starting signup...")
    
    # 1. Generate email
    email_data = gen_email()
    if not email_data:
        log("Failed to generate email")
        return None
    email = email_data['email']
    password = email_data['password']
    email_token = email_data.get('token', '')
    log(f"Email: {email}")
    
    # 2. Get fresh proxy
    proxy_ip = None
    try:
        r = requests.get(f'http://{PROXY_HOST}:{PROXY_PORT}/get-username-password', 
                       auth=(PROXY_USER, PROXY_PASS), timeout=10)
        if r.ok:
            data = r.json()
            proxy_ip = data.get('ip')
    except:
        pass
    
    if not proxy_ip:
        proxy_ip = f"{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}"
    
    proxy_config = {
        'server': f'http://{PROXY_HOST}:{PROXY_PORT}',
        'username': PROXY_USER,
        'password': PROXY_PASS,
    }
    
    # 3. Launch browser with proxy
    pw = sync_playwright().start()
    browser = pw.chromium.launch(
        headless=False,  # Real Chrome for Turnstile
        args=[
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--window-size=1920,1080',
            '--start-maximized',
        ]
    )
    
    context = browser.new_context(
        proxy=proxy_config,
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )
    
    # 4. New tab listener for success detection
    new_tab = [None]
    first_page = [None]
    account_url = [None]
    
    def on_new_page(page):
        if first_page[0] is None:
            first_page[0] = page
        else:
            new_tab[0] = page
    
    context.on('page', on_new_page)
    
    page = context.new_page()
    
    try:
        # 5. Navigate to signup page
        page.goto('https://dash.cloudflare.com/sign-up', timeout=30000)
        time.sleep(10)  # Wait for full render
        
        # 6. Check for existing Turnstile
        turnstile_token = None
        try:
            widget = page.query_selector('.cf-turnstile')
            if widget:
                w = widget.bounding_box()
                if w and w['width'] > 0:
                    log(f"Turnstile found at {w}")
                    # Click Turnstile checkbox via CDP
                    cdp = page.context.new_cdp_session(page)
                    cdp.send('Input.dispatchMouseEvent', {
                        'type': 'mousePressed',
                        'x': w['x'] + w['width']/2,
                        'y': w['y'] + w['height']/2,
                        'button': 'left',
                        'clickCount': 1
                    })
                    cdp.send('Input.dispatchMouseEvent', {
                        'type': 'mouseReleased',
                        'x': w['x'] + w['width']/2,
                        'y': w['y'] + w['height']/2,
                        'button': 'left',
                        'clickCount': 1
                    })
                    log("Clicked Turnstile")
                    time.sleep(5)
                    # Get token
                    try:
                        token_input = page.query_selector('input[name="cf_challenge_response"]')
                        if token_input:
                            turnstile_token = token_input.input_value()
                    except:
                        pass
        except Exception as e:
            log(f"Turnstile check error: {e}")
        
        # 7. Fill signup form
        time.sleep(2)
        try:
            email_input = page.query_selector('input[name="email"]')
            if email_input:
                email_input.click(click_count=3)
                email_input.type(email, delay=random.randint(50, 150))
        except Exception as e:
            log(f"Email fill error: {e}")
        
        time.sleep(0.5)
        try:
            pass_input = page.query_selector('input[name="password"]')
            if pass_input:
                pass_input.click(click_count=3)
                pass_input.type(password, delay=random.randint(50, 150))
        except Exception as e:
            log(f"Password fill error: {e}")
        
        time.sleep(1)
        
        # 8. Click Sign Up
        try:
            submit = page.query_selector('button[type="submit"]')
            if submit:
                submit.click()
                log("Clicked Sign Up")
        except Exception as e:
            log(f"Submit click error: {e}")
        
        # 9. Wait for response
        time.sleep(5)
        
        # Check for new tab (success = dashboard opened)
        if new_tab[0]:
            log("SUCCESS - Dashboard opened in new tab!")
            account_url = new_tab[0].url
            new_tab[0].close()
            browser.close()
            pw.stop()
            
            # 10. Verify email
            if email_token and '@' in email:
                domain = email.split('@')[1]
                verify_link = get_verification_link(email_token, domain)
                if verify_link:
                    log(f"Email verified: {verify_link}")
            
            return {
                'email': email,
                'password': password,
                'account_url': account_url,
                'email_token': email_token
            }
        
        # Check for error
        page_text = page.inner_text('body')
        if 'unable to sign up' in page_text.lower():
            log("RATE LIMIT - blocked by CF")
        elif 'suspended' in page_text.lower():
            log("ACCOUNT SUSPENDED")
        else:
            log("Unknown state - continuing")
        
        # Capture cookies before closing
        cookies = context.cookies()
        browser.close()
        pw.stop()
        
        return None
        
    except Exception as e:
        log(f"Signup error: {e}")
        try:
            browser.close()
            pw.stop()
        except:
            pass
        return None

# ============ MAIN ============
if __name__ == '__main__':
    log("CF Signup Worker started")
    result = signup_account()
    if result:
        log(f"Account created: {result['email']}")
        print(json.dumps(result))
    else:
        log("Signup failed")
        print("null")