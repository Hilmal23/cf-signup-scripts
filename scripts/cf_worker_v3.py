#!/usr/bin/env python3
"""CF Signup Worker v3 - Fixed: path + detection + save"""
import os, sys, json, time, random, re, requests
from pathlib import Path
from playwright.sync_api import sync_playwright

WORKER_ID = int(os.environ.get('WORKER_ID', '0'))
LOG_DIR = Path('/tmp')
LOG_FILE = LOG_DIR / f'cf_worker_{WORKER_ID}.log'
PROGRESS_FILE = Path(f'/home/ubuntu/cf-automation-suite/progress.json')
ACCOUNTS_FILE = Path(f'/home/ubuntu/cf-automation-suite/accounts_new.txt')

PROXY_HOST = 'prod-proxy.geonode.io'
PROXY_PORT = '9000'
PROXY_USER = 'geonode_RTwCdAt5Br-type-residential-country-us'
PROXY_PASS = '34c063a6-055f-42e0-980d-57db761b8c46'

def log(msg):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] [Worker-{WORKER_ID}] {msg}\n"
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

def click_turnstile(page):
    try:
        for attempt in range(20):
            try:
                widget = page.query_selector('.cf-turnstile')
                if widget:
                    w = widget.bounding_box()
                    if w and w['width'] > 50 and w['height'] > 50:
                        log(f"Turnstile: {w['width']}x{w['height']}")
                        cdp = page.context.new_cdp_session(page)
                        cx, cy = w['x'] + w['width']/2, w['y'] + w['height']/2
                        cdp.send('Input.dispatchMouseEvent', {
                            'type': 'mousePressed', 'x': cx, 'y': cy, 'button': 'left', 'clickCount': 1
                        })
                        cdp.send('Input.dispatchMouseEvent', {
                            'type': 'mouseReleased', 'x': cx, 'y': cy, 'button': 'left', 'clickCount': 1
                        })
                        log(f"Clicked Turnstile at ({cx:.0f},{cy:.0f})")
                        time.sleep(5)
                        return True
            except: pass
            time.sleep(1)
        log("No Turnstile widget found - proceeding anyway")
        return True
    except Exception as e:
        log(f"Turnstile error: {e}")
        return True

def fill_form(page, email, password):
    try:
        time.sleep(2)
        for inp in ['input[name="email"]', 'input[type="email"]']:
            el = page.query_selector(inp)
            if el:
                el.click(click_count=3)
                for c in email: el.type(c, delay=random.randint(30, 100))
                log(f"Filled email")
                break
        time.sleep(random.uniform(0.3, 0.8))
        for inp in ['input[name="password"]', 'input[type="password"]']:
            el = page.query_selector(inp)
            if el:
                el.click(click_count=3)
                for c in password: el.type(c, delay=random.randint(30, 100))
                log(f"Filled password")
                break
        time.sleep(random.uniform(0.5, 1.5))
    except Exception as e:
        log(f"Fill error: {e}")

def signup_account():
    log("Starting signup...")
    email_data = gen_email()
    if not email_data:
        log("Email gen failed")
        return None
    email = email_data['email']
    password = email_data['password']
    email_token = email_data.get('token', '')
    log(f"Email: {email}")

    proxy = {'server': f'http://{PROXY_HOST}:{PROXY_PORT}', 'username': PROXY_USER, 'password': PROXY_PASS}

    pw = sync_playwright().start()
    browser = pw.chromium.launch(
        headless=False,
        args=['--no-sandbox','--disable-dev-shm-usage','--disable-gpu','--window-size=1920,1080','--start-maximized']
    )

    new_tab_ref = [None]
    first_page_ref = [None]

    def on_new_page(page):
        if first_page_ref[0] is None:
            first_page_ref[0] = page
        else:
            new_tab_ref[0] = page
            log(f"NEW TAB: {page.url}")

    context = browser.new_context(
        proxy=proxy,
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )
    context.on('page', on_new_page)
    page = context.new_page()

    try:
        log("Going to CF signup...")
        page.goto('https://dash.cloudflare.com/sign-up', timeout=30000)
        time.sleep(10)

        click_turnstile(page)
        fill_form(page, email, password)

        log("Submitting...")
        try:
            btn = page.query_selector('button[type="submit"]')
            if btn: btn.click()
            else: page.keyboard.press('Enter')
        except:
            page.keyboard.press('Enter')

        # Wait up to 30s for new tab (dashboard opens in new tab on success)
        verify_link = None
        for i in range(30):
            time.sleep(1)
            if new_tab_ref[0]:
                tab = new_tab_ref[0]
                tab_url = tab.url
                log(f"NEW TAB URL: {tab_url}")

                # Close new tab, get back to original
                tab.close()

                # Verify email
                if email_token:
                    domain = email.split('@')[1]
                    verify_link = get_verification_link(email_token, domain)
                    if verify_link:
                        log(f"Got verify link!")

                # Save account
                ACCOUNTS_FILE.parent.mkdir(exist_ok=True, parents=True)
                result = {'email': email, 'password': password, 'dashboard_url': tab_url,
                          'verified': bool(verify_link)}
                with open(ACCOUNTS_FILE, 'a') as f:
                    f.write(json.dumps(result) + '\n')

                # Update progress
                progress = {}
                if PROGRESS_FILE.exists():
                    progress = json.loads(PROGRESS_FILE.read_text())
                progress['count'] = progress.get('count', 0) + 1
                PROGRESS_FILE.write_text(json.dumps(progress, indent=2))

                log(f"ACCOUNT SAVED! Total: {progress['count']}")
                browser.close()
                pw.stop()
                return result

            if i % 5 == 0:
                log(f"Waiting... ({i}s) URL: {page.url}")

        # Timeout
        log("TIMEOUT - no new tab")
        browser.close()
        pw.stop()
        return None

    except Exception as e:
        log(f"Error: {e}")
        import traceback; log(traceback.format_exc())
        try: browser.close(); pw.stop()
        except: pass
        return None

if __name__ == '__main__':
    result = signup_account()
    if result:
        print(json.dumps(result))
    else:
        print("null")