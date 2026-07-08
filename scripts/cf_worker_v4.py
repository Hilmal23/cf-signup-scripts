#!/usr/bin/env python3
"""CF Signup Worker v4 - Detect account via API response, not redirect"""
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

def click_turnstile(page):
    for attempt in range(25):
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
    log("No Turnstile - proceeding without click")
    return True

def fill_form(page, email, password):
    time.sleep(2)
    for sel in ['input[name="email"]', 'input[type="email"]', 'input#email']:
        el = page.query_selector(sel)
        if el:
            el.click(click_count=3)
            for c in email: el.type(c, delay=random.randint(30, 100))
            break
    time.sleep(random.uniform(0.3, 0.8))
    for sel in ['input[name="password"]', 'input[type="password"]', 'input#password']:
        el = page.query_selector(sel)
        if el:
            el.click(click_count=3)
            for c in password: el.type(c, delay=random.randint(30, 100))
            break
    time.sleep(random.uniform(0.5, 1.5))

def signup_account():
    log("Starting...")
    email_data = gen_email()
    if not email_data:
        log("Email gen failed"); return None
    email, password, email_token = email_data['email'], email_data['password'], email_data.get('token', '')
    log(f"Email: {email}")

    proxy = {'server': f'http://{PROXY_HOST}:{PROXY_PORT}', 'username': PROXY_USER, 'password': PROXY_PASS}

    pw = sync_playwright().start()
    browser = pw.chromium.launch(
        headless=False,
        args=['--no-sandbox','--disable-dev-shm-usage','--disable-gpu','--window-size=1920,1080','--start-maximized']
    )
    context = browser.new_context(proxy=proxy, viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    page = context.new_page()

    # New tab listener
    new_tab_ref = [None]
    def on_new_page(p):
        new_tab_ref[0] = p
        log(f"NEW TAB: {p.url}")
    context.on('page', on_new_page)

    try:
        log("Navigating...")
        page.goto('https://dash.cloudflare.com/sign-up', timeout=30000)
        time.sleep(10)
        title = page.title()
        log(f"Title: {title}")

        click_turnstile(page)
        fill_form(page, email, password)

        log("Submitting...")
        try:
            btn = page.query_selector('button[type="submit"]')
            if btn: btn.click()
            else: page.keyboard.press('Enter')
        except: page.keyboard.press('Enter')

        # Wait for response - up to 45s
        for i in range(45):
            time.sleep(1)

            # Check 1: New tab opened (dashboard)
            if new_tab_ref[0]:
                tab = new_tab_ref[0]
                tab_url = tab.url
                log(f"DASHBOARD TAB: {tab_url}")
                tab.close()

                verify_link = None
                if email_token:
                    verify_link = get_verification_link(email_token, email.split('@')[1])

                ACCOUNTS_FILE.parent.mkdir(exist_ok=True, parents=True)
                result = {'email': email, 'password': password, 'dashboard_url': tab_url,
                          'verified': bool(verify_link)}
                with open(ACCOUNTS_FILE, 'a') as f: f.write(json.dumps(result) + '\n')

                progress = json.loads(PROGRESS_FILE.read_text()) if PROGRESS_FILE.exists() else {}
                progress['count'] = progress.get('count', 0) + 1
                PROGRESS_FILE.write_text(json.dumps(progress))
                log(f"SAVED! Total: {progress['count']}")

                browser.close(); pw.stop()
                return result

            # Check 2: URL changed to dashboard/overview
            cur_url = page.url
            if 'overview' in cur_url or 'home' in cur_url:
                log(f"REDIRECT to: {cur_url}")
                verify_link = None
                if email_token:
                    verify_link = get_verification_link(email_token, email.split('@')[1])

                ACCOUNTS_FILE.parent.mkdir(exist_ok=True, parents=True)
                result = {'email': email, 'password': password, 'dashboard_url': cur_url,
                          'verified': bool(verify_link)}
                with open(ACCOUNTS_FILE, 'a') as f: f.write(json.dumps(result) + '\n')

                progress = json.loads(PROGRESS_FILE.read_text()) if PROGRESS_FILE.exists() else {}
                progress['count'] = progress.get('count', 0) + 1
                PROGRESS_FILE.write_text(json.dumps(progress))
                log(f"SAVED! Total: {progress['count']}")

                browser.close(); pw.stop()
                return result

            # Check 3: "already exists" or account created - check via API
            # Try to login via API with the account credentials
            if i >= 5:
                try:
                    r = requests.post('https://dash.cloudflare.com/api/v4/login',
                        json={'email': email, 'password': password},
                        headers={'Content-Type': 'application/json'},
                        timeout=10)
                    if r.ok or (r.status_code == 400 and 'already' in r.text.lower()):
                        log(f"Account exists! API status: {r.status_code}")
                        ACCOUNTS_FILE.parent.mkdir(exist_ok=True, parents=True)
                        result = {'email': email, 'password': password, 'dashboard_url': 'pending_verification',
                                  'verified': False}
                        with open(ACCOUNTS_FILE, 'a') as f: f.write(json.dumps(result) + '\n')
                        progress = json.loads(PROGRESS_FILE.read_text()) if PROGRESS_FILE.exists() else {}
                        progress['count'] = progress.get('count', 0) + 1
                        PROGRESS_FILE.write_text(json.dumps(progress))
                        log(f"SAVED (email pending)! Total: {progress['count']}")
                        browser.close(); pw.stop()
                        return result
                except: pass

            # Check 4: Error alert
            try:
                err = page.query_selector('[role="alert"]')
                if err:
                    err_text = err.inner_text()
                    log(f"Alert: {err_text[:100]}")
                    if 'unable' in err_text.lower() or 'suspended' in err_text.lower():
                        break
            except: pass

            if i % 10 == 0:
                log(f"Waiting {i}s | URL: {cur_url}")

        log("TIMEOUT - no success detected")
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