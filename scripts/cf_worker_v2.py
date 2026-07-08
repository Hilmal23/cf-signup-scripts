#!/usr/bin/env python3
"""CF Signup Worker v2 - Fixed detection + better Turnstile handling"""
import os, sys, json, time, random, re, requests, socket
from pathlib import Path
from playwright.sync_api import sync_playwright

# ============ CONFIG ============
WORKER_ID = int(os.environ.get('WORKER_ID', '0'))
LOG_DIR = Path('/tmp')
LOG_FILE = LOG_DIR / f'cf_worker_{WORKER_ID}.log'
PROGRESS_FILE = Path('/root/cf-automation-suite/progress.json')
ACCOUNTS_FILE = Path('/root/cf-automation-suite/accounts_new.txt')

PROXY_HOST = 'prod-proxy.geonode.io'
PROXY_PORT = '9000'
PROXY_USER = 'geonode_RTwCdAt5Br-type-residential-country-us'
PROXY_PASS = '34c063a6-055f-42e0-980d-57db761b8c46'

# ============ LOGGING ============
def log(msg):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] [Worker-{WORKER_ID}] {msg}\n"
    with open(LOG_FILE, 'a') as f:
        f.write(line)
    print(line.strip())

def log_always(msg):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [Worker-{WORKER_ID}] {msg}")

# ============ EMAIL ============
def gen_email():
    try:
        r = requests.get('https://api.mail.tm/domains', timeout=10)
        if not r.ok: return None
        domains = r.json().get('hydra:member', [])
        if not domains: return None
        
        domain = domains[0]['domain']
        username = f"cf{random.randint(100000,999999)}{random.randint(1000,9999)}"
        email = f"{username}@{domain}"
        password = f"CfPass{random.randint(10000,99999)}!"
        
        r2 = requests.post('https://api.mail.tm/accounts', json={
            'address': email, 'password': password
        }, timeout=10)
        if r2.ok:
            return {'email': email, 'password': password, 'token': r2.json().get('token')}
        return None
    except Exception as e:
        log(f"Email gen error: {e}")
        return None

def get_verification_link(token, domain):
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
        except: pass
    return None

# ============ WAIT FOR TURNSTILE ============
def wait_for_turnstile(page, timeout=15):
    """Wait for Turnstile widget to appear and be clickable"""
    for _ in range(timeout):
        try:
            widget = page.query_selector('.cf-turnstile')
            if widget:
                w = widget.bounding_box()
                if w and w['width'] > 50 and w['height'] > 50:
                    log(f"Turnstile ready: {w['width']}x{w['height']}")
                    return widget, w
        except: pass
        time.sleep(1)
    log("Turnstile not found")
    return None, None

# ============ CLICK TURNSTILE VIA CDP ============
def click_turnstile(page):
    """Click Turnstile checkbox using CDP Input.dispatchMouseEvent"""
    try:
        widget, w = wait_for_turnstile(page, timeout=20)
        if not widget or not w:
            log("No Turnstile widget found")
            return False
        
        # CDP click at center of widget
        cdp = page.context.new_cdp_session(page)
        cx, cy = w['x'] + w['width']/2, w['y'] + w['height']/2
        
        cdp.send('Input.dispatchMouseEvent', {
            'type': 'mousePressed', 'x': cx, 'y': cy,
            'button': 'left', 'clickCount': 1
        })
        cdp.send('Input.dispatchMouseEvent', {
            'type': 'mouseReleased', 'x': cx, 'y': cy,
            'button': 'left', 'clickCount': 1
        })
        log(f"Clicked Turnstile at ({cx:.0f}, {cy:.0f})")
        
        # Wait for solve (widget disappears or gets checked)
        for _ in range(10):
            time.sleep(1)
            try:
                # Check if widget is still visible/challenged
                remaining = page.query_selector('.cf-turnstile')
                if remaining:
                    r = remaining.bounding_box()
                    if r and r['width'] < 50:
                        log("Turnstile solved (widget minimized)")
                        return True
                else:
                    log("Turnstile solved (widget removed)")
                    return True
            except: pass
        
        return True  # Assume solved even if we can't detect
    except Exception as e:
        log(f"Turnstile click error: {e}")
        return False

# ============ FILL FORM ============
def fill_signup_form(page, email, password):
    """Fill CF signup form with human-like typing"""
    try:
        # Wait for form to render
        time.sleep(2)
        
        # Email
        try:
            email_input = page.query_selector('input[name="email"]')
            if not email_input:
                email_input = page.query_selector('input[type="email"]')
            if email_input:
                email_input.click(click_count=3)
                for c in email:
                    email_input.type(c, delay=random.randint(50, 150))
                log(f"Filled email: {email}")
        except Exception as e:
            log(f"Email fill error: {e}")
        
        time.sleep(random.uniform(0.3, 0.8))
        
        # Password
        try:
            pass_input = page.query_selector('input[name="password"]')
            if not pass_input:
                pass_input = page.query_selector('input[type="password"]')
            if pass_input:
                pass_input.click(click_count=3)
                for c in password:
                    pass_input.type(c, delay=random.randint(50, 150))
                log("Filled password")
        except Exception as e:
            log(f"Password fill error: {e}")
        
        time.sleep(random.uniform(0.5, 1.5))
        return True
    except Exception as e:
        log(f"Fill form error: {e}")
        return False

# ============ SIGNUP ============
def signup_account():
    log("Starting signup...")
    
    # Generate email
    email_data = gen_email()
    if not email_data:
        log("Failed to generate email")
        return None
    email = email_data['email']
    password = email_data['password']
    email_token = email_data.get('token', '')
    log(f"Email: {email}")
    
    # Proxy config
    proxy = {
        'server': f'http://{PROXY_HOST}:{PROXY_PORT}',
        'username': PROXY_USER,
        'password': PROXY_PASS,
    }
    
    # Launch browser
    pw = sync_playwright().start()
    browser = pw.chromium.launch(
        headless=False,
        args=[
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--window-size=1920,1080',
            '--start-maximized',
            '--disable-blink-features=AutomationControlled',
        ]
    )
    
    context = browser.new_context(
        proxy=proxy,
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )
    
    # New tab listener - registered BEFORE navigation
    new_tab_ref = [None]
    
    def on_new_page(page):
        new_tab_ref[0] = page
        log(f"NEW TAB OPENED: {page.url}")
    
    context.on('page', on_new_page)
    
    page = context.new_page()
    
    try:
        # Navigate
        log("Navigating to CF signup...")
        page.goto('https://dash.cloudflare.com/sign-up', timeout=30000)
        time.sleep(10)  # Wait for React to render
        
        # Check page loaded
        title = page.title()
        log(f"Page title: {title}")
        
        # Click Turnstile
        click_turnstile(page)
        time.sleep(3)
        
        # Fill form
        fill_signup_form(page, email, password)
        time.sleep(1)
        
        # Click Sign Up
        log("Clicking Sign Up...")
        try:
            submit = page.query_selector('button[type="submit"]')
            if submit:
                submit.click()
            else:
                # Try Enter key
                page.keyboard.press('Enter')
        except Exception as e:
            log(f"Submit click error: {e}")
            page.keyboard.press('Enter')
        
        log("Sign Up clicked - waiting for response...")
        
        # Wait for navigation or new tab (up to 30s)
        max_wait = 30
        for i in range(max_wait):
            time.sleep(1)
            
            # Check new tab first (dashboard opens in new tab on success)
            if new_tab_ref[0]:
                new_tab = new_tab_ref[0]
                log(f"NEW TAB detected! URL: {new_tab.url}")
                dashboard_url = new_tab.url
                new_tab.close()
                
                # Verify email
                if email_token:
                    domain = email.split('@')[1]
                    verify_link = get_verification_link(email_token, domain)
                    if verify_link:
                        log(f"Got verification link!")
                
                browser.close()
                pw.stop()
                
                return {
                    'email': email,
                    'password': password,
                    'dashboard_url': dashboard_url,
                    'email_token': email_token,
                    'verified': bool(verify_link) if email_token else False
                }
            
            # Check current page state
            current_url = page.url
            current_title = page.title()
            
            if 'dashboard' in current_url.lower() or 'overview' in current_url.lower():
                log(f"SUCCESS! Current page redirected: {current_url}")
                browser.close()
                pw.stop()
                return {'email': email, 'password': password, 'dashboard_url': current_url}
            
            if 'sign-up' not in current_url.lower() and 'signup' not in current_url.lower():
                log(f"URL changed away from signup: {current_url}")
            
            # Check for error messages
            try:
                err = page.query_selector('[role="alert"]')
                if err:
                    err_text = err.inner_text()
                    log(f"Error alert: {err_text}")
                    if 'unable to sign up' in err_text.lower():
                        log("RATE LIMIT detected")
                        break
                    if 'suspended' in err_text.lower():
                        log("ACCOUNT SUSPENDED")
                        break
            except: pass
            
            if i % 5 == 0:
                log(f"Waiting... ({i}s) URL: {current_url}")
        
        # Timeout - no new tab, no redirect
        log("TIMEOUT - no redirect detected")
        
        # Try to get page text for debugging
        try:
            body_text = page.inner_text('body')
            if 'cloudflare' in body_text.lower():
                log(f"Still on CF page, title: {page.title()}")
        except: pass
        
        browser.close()
        pw.stop()
        return None
        
    except Exception as e:
        log(f"FATAL error: {e}")
        import traceback
        log(traceback.format_exc())
        try:
            browser.close()
            pw.stop()
        except: pass
        return None

# ============ MAIN ============
if __name__ == '__main__':
    log("CF Worker v2 started")
    result = signup_account()
    
    if result:
        log(f"SUCCESS: {result['email']}")
        # Save to accounts file
        ACCOUNTS_FILE.parent.mkdir(exist_ok=True)
        with open(ACCOUNTS_FILE, 'a') as f:
            f.write(json.dumps(result) + '\n')
        
        # Update progress
        progress = {}
        if PROGRESS_FILE.exists():
            progress = json.loads(PROGRESS_FILE.read_text())
        progress['count'] = progress.get('count', 0) + 1
        PROGRESS_FILE.write_text(json.dumps(progress, indent=2))
        
        print(json.dumps(result))
    else:
        log("Signup failed")
        print("null")