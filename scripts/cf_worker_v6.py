#!/usr/bin/env python3
"""CF Signup Worker v6 - Debug page text, clear all state"""
import os, sys, json, time, random, re, requests
from pathlib import Path
from playwright.sync_api import sync_playwright

WORKER_ID = int(os.environ.get('WORKER_ID', '0'))
LOG_FILE = Path(f'/tmp/cf_worker_{WORKER_ID}.log')
ACCOUNTS_FILE = Path(f'/home/ubuntu/cf-automation-suite/accounts_new.txt')
PROGRESS_FILE = Path(f'/home/ubuntu/cf-automation-suite/progress.json')

PROXY_HOST = 'prod-proxy.geonode.io'
PROXY_PORT = '9000'
PROXY_USER = 'geonode_RTwCdAt5Br-type-residential-country-us'
PROXY_PASS = '34c063a6-055f-42e0-980d-57db761b8c46'

def log(msg):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] [W{WORKER_ID}] {msg}\n"
    with open(LOG_FILE, 'a') as f: f.write(line)
    print(line.strip())

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
        log(f"Email err: {e}")
        return None

def get_messages(token, domain):
    headers = {'Authorization': f'Bearer {token}'}
    try:
        r = requests.get('https://api.mail.tm/messages', headers=headers, timeout=10)
        if r.ok:
            return r.json().get('hydra:member', [])
    except: pass
    return []

def get_verification_link(token, domain):
    for attempt in range(60):
        msgs = get_messages(token, domain)
        for m in msgs:
            subj = m.get('subject', '').lower()
            if 'cloudflare' in subj or 'verify' in subj or 'confirm' in subj:
                msg_id = m['id']
                headers = {'Authorization': f'Bearer {token}'}
                try:
                    r = requests.get(f'https://api.mail.tm/messages/{msg_id}', headers=headers, timeout=10)
                    if r.ok:
                        body = r.json().get('text', '') or r.json().get('html', '')
                        links = re.findall(r'https?://[^\s<>"\'\\]+', body)
                        for link in links:
                            if any(k in link.lower() for k in ['verify', 'confirm', 'activation', '/sign-up']):
                                log(f"VERIFICATION LINK FOUND!")
                                return link
                except: pass
        time.sleep(2)
    log("No verification email")
    return None

def click_turnstile(page):
    for _ in range(25):
        try:
            widget = page.query_selector('.cf-turnstile')
            if widget:
                w = widget.bounding_box()
                if w and w['width'] > 50 and w['height'] > 50:
                    log(f"Turnstile: {w['width']:.0f}x{w['height']:.0f}")
                    cdp = page.context.new_cdp_session(page)
                    cx, cy = w['x'] + w['width']/2, w['y'] + w['height']/2
                    cdp.send('Input.dispatchMouseEvent', {'type': 'mousePressed', 'x': cx, 'y': cy, 'button': 'left', 'clickCount': 1})
                    cdp.send('Input.dispatchMouseEvent', {'type': 'mouseReleased', 'x': cx, 'y': cy, 'button': 'left', 'clickCount': 1})
                    log(f"Clicked TS at ({cx:.0f},{cy:.0f})")
                    time.sleep(5)
                    return True
        except: pass
        time.sleep(1)
    log("No Turnstile")
    return True

def fill_form(page, email, password):
    time.sleep(2)
    for sel in ['input[name="email"]', 'input[type="email"]']:
        el = page.query_selector(sel)
        if el:
            el.click(click_count=3)
            for c in email: el.type(c, delay=random.randint(30, 100))
            log(f"Email: {email}")
            break
    time.sleep(random.uniform(0.3, 0.8))
    for sel in ['input[name="password"]', 'input[type="password"]']:
        el = page.query_selector(sel)
        if el:
            el.click(click_count=3)
            for c in password: el.type(c, delay=random.randint(30, 100))
            log("Password filled")
            break
    time.sleep(random.uniform(0.5, 1.5))

def save_account(result):
    ACCOUNTS_FILE.parent.mkdir(exist_ok=True, parents=True)
    with open(ACCOUNTS_FILE, 'a') as f:
        f.write(json.dumps(result) + '\n')
    progress = json.loads(PROGRESS_FILE.read_text()) if PROGRESS_FILE.exists() else {}
    progress['count'] = progress.get('count', 0) + 1
    PROGRESS_FILE.write_text(json.dumps(progress))
    log(f"SAVED! Total: {progress['count']}")

def debug_page_text(page):
    """Debug: print page body text after submit"""
    try:
        body = page.inner_text('body')
        log(f"PAGE TEXT ({len(body)} chars): {body[:500]}")
        return body
    except Exception as e:
        log(f"Could not get page text: {e}")
        return ""

def signup_account():
    log("Starting CF signup...")
    email_data = gen_email()
    if not email_data:
        log("Email gen failed"); return None
    email, password, email_token = email_data['email'], email_data['password'], email_data.get('token', '')
    log(f"Email: {email}")

    proxy = {'server': f'http://{PROXY_HOST}:{PROXY_PORT}', 'username': PROXY_USER, 'password': PROXY_PASS}

    # FRESH browser per attempt - critical for email uniqueness
    pw = sync_playwright().start()
    browser = pw.chromium.launch(
        headless=False,
        args=['--no-sandbox','--disable-dev-shm-usage','--disable-gpu','--window-size=1920,1080','--start-maximized']
    )
    context = browser.new_context(proxy=proxy, viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    context.clear_cookies()
    page = context.new_page()
    page.evaluate('() => { try { localStorage.clear(); sessionStorage.clear(); document.cookie=""; } catch(e) {} }')

    new_tab_ref = [None]
    def on_new_page(p):
        new_tab_ref[0] = p
        log(f"NEW TAB: {p.url}")
    context.on('page', on_new_page)

    try:
        log("Navigating to CF signup...")
        page.goto('https://dash.cloudflare.com/sign-up', timeout=60000)
        
        # CRITICAL: Wait for "Just a moment..." challenge to resolve FIRST
        # This is CF's Bot Management check - it must complete before form renders
        for wait_attempt in range(60):  # up to 60s
            try:
                title = page.title()
                url = page.url
                if title != 'Just a moment...' and 'challenge' not in title.lower():
                    log(f"Challenge resolved! Title: {title} | URL: {url}")
                    break
            except: pass
            time.sleep(1)
        else:
            log("Challenge did not resolve in 60s")
            browser.close(); pw.stop()
            return None
        
        time.sleep(5)  # Extra wait for React SPA to fully render after challenge
        
        log(f"Title: {page.title()}")

        click_turnstile(page)
        fill_form(page, email, password)

        log("Submitting...")
        try:
            btn = page.query_selector('button[type="submit"]')
            if btn: btn.click()
            else: page.keyboard.press('Enter')
        except: page.keyboard.press('Enter')

        # Wait up to 60s for response
        domain = email.split('@')[1]
        account_id = ''
        dashboard_url = ''
        verified = False

        for i in range(60):
            time.sleep(1)

            # Check 1: new tab = dashboard
            if new_tab_ref[0]:
                tab = new_tab_ref[0]
                tab_url = tab.url
                log(f"DASHBOARD TAB: {tab_url}")
                tab.close()

                parts = tab_url.split('/')
                for j, p in enumerate(parts):
                    if p and '-' in p and len(p) > 20:
                        account_id = p
                        dashboard_url = tab_url
                        break

                verify_link = get_verification_link(email_token, domain)
                if verify_link:
                    page.goto(verify_link, timeout=15000)
                    time.sleep(3)
                    verified = True
                    cur = page.url
                    log(f"After verify: {cur}")

                result = {'email': email, 'password': password, 'account_id': account_id,
                          'dashboard_url': dashboard_url, 'verified': verified}
                save_account(result)
                browser.close(); pw.stop()
                return result

            # Check 2: URL redirect
            cur_url = page.url
            if 'overview' in cur_url or ('dash.cloudflare.com/' in cur_url and 'sign-up' not in cur_url):
                log(f"REDIRECT: {cur_url}")
                result = {'email': email, 'password': password, 'account_id': account_id,
                          'dashboard_url': cur_url, 'verified': verified}
                save_account(result)
                browser.close(); pw.stop()
                return result

            # Check 3: Page text analysis (wait at least 3s first)
            if i >= 3:
                try:
                    body = page.inner_text('body').lower()

                    # Account created - email verification sent
                    if any(k in body for k in ['check your email', 'verify your email',
                            'confirmation', 'sent a link', 'sent to', 'click the link',
                            'email has been sent', 'verify link']):
                        log("ACCOUNT CREATED - checking email...")

                        verify_link = get_verification_link(email_token, domain)
                        if verify_link:
                            log(f"Got verify link!")
                            page.goto(verify_link, timeout=15000)
                            time.sleep(3)
                            verified = True
                            cur_url = page.url
                            log(f"After verify: {cur_url}")
                            parts = cur_url.split('/')
                            for j, p in enumerate(parts):
                                if p and '-' in p and len(p) > 20:
                                    account_id = p
                                    dashboard_url = cur_url
                                    break

                        result = {'email': email, 'password': password, 'account_id': account_id,
                                  'dashboard_url': dashboard_url, 'verified': verified}
                        save_account(result)
                        browser.close(); pw.stop()
                        return result

                    # Account already exists
                    if 'already' in body and 'account' in body:
                        log("ACCOUNT EXISTS - check if email actually registered")
                        # Try to verify - if email exists, verification should come
                        verify_link = get_verification_link(email_token, domain)
                        if verify_link:
                            log("Email exists! Verifying...")
                            page.goto(verify_link, timeout=15000)
                            time.sleep(3)
                            verified = True
                            cur_url = page.url
                            parts = cur_url.split('/')
                            for j, p in enumerate(parts):
                                if p and '-' in p and len(p) > 20:
                                    account_id = p
                                    dashboard_url = cur_url
                                    break
                            result = {'email': email, 'password': password, 'account_id': account_id,
                                      'dashboard_url': dashboard_url, 'verified': verified}
                        else:
                            log("Email NOT found - false positive, retry needed")
                            result = None
                        browser.close(); pw.stop()
                        return result

                    # Blocked/suspended
                    if any(k in body for k in ['unable', 'suspended', 'blocked', 'prohibited']):
                        log(f"BLOCKED: {body[:200]}")
                        break
                except Exception as e:
                    log(f"Page text error: {e}")

            if i % 10 == 0:
                log(f"Waiting {i}s | {page.url}")

        log("TIMEOUT")
        debug_page_text(page)
        browser.close(); pw.stop()
        return None

    except Exception as e:
        log(f"Error: {e}")
        import traceback; log(traceback.format_exc())
        try: browser.close(); pw.stop()
        except: pass
        return None

if __name__ == '__main__':
    result = signup_account()
    print(json.dumps(result) if result else "null")