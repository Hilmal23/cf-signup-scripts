#!/usr/bin/env python3
"""CF Signup - check if account exists despite 400 + try with existing session"""
from playwright.sync_api import sync_playwright
import requests, time, json

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

email = f"cf{int(time.time())}@hilmal.store"
pw = "CfSignup123!"
log(f"Email: {email}")

BRD = 'http://brd-customer-hl_c0f6789c-zone-web_unlocker1:ds3ovbwhs69y@brd.superproxy.io:33335'

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        executable_path="/snap/chromium/current/usr/lib/chromium-browser/chrome",
        args=[
            "--no-sandbox", "--disable-setuid-sandbox",
            "--ignore-certificate-errors",
            "--allow-running-insecure-content",
            "--ignore-certificate-errors-spki-list=*",
        ]
    )
    ctx = browser.new_context(
        proxy={"server": "http://brd.superproxy.io:33335", "username": "brd-customer-hl_c0f6789c-zone-web_unlocker1", "password": "ds3ovbwhs69y"},
    )
    page = ctx.new_page()
    
    log("Loading page via BD...")
    page.goto("https://dash.cloudflare.com/sign-up", timeout=90000)
    time.sleep(8)
    
    cookies = ctx.cookies()
    cookie_dict = {c['name']: c['value'] for c in cookies}
    
    page.fill('input[name="email"]', email)
    page.fill('input[name="password"]', pw)
    
    captured = [None]
    def on_request(request):
        if '/api/v4/user/create' in request.url and request.method == 'POST':
            captured[0] = {'headers': dict(request.headers), 'body': request.post_data}
    
    page.on("request", on_request)
    page.click('button[type="submit"]')
    time.sleep(8)
    
    log(f"After - Title: {page.title()}")
    log(f"After - URL: {page.url}")
    
    if captured[0]:
        req = captured[0]
        
        # Check email inbox via IMAP
        log("\n=== Checking email inbox ===")
        import imaplib, email as emaillib
        try:
            mail = imaplib.IMAP4_SSL('localhost', 993)
            mail.login('cfmail', 'CfMail2024!')
            mail.select('INBOX')
            status, msgs = mail.search(None, 'ALL')
            log(f"Total emails in inbox: {len(msgs[0].split())}")
            
            # Check latest email
            if msgs[0].split():
                latest_id = msgs[0].split()[-1]
                status, msg_data = mail.fetch(latest_id, '(RFC822)')
                msg = emaillib.message_from_bytes(msg_data[0][1])
                log(f"Latest email from: {msg['From']}")
                log(f"Subject: {msg['Subject']}")
                body = ''
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == 'text/plain':
                            body = part.get_payload()
                            break
                else:
                    body = msg.get_payload()
                log(f"Body preview: {body[:200]}")
            mail.logout()
        except Exception as e:
            log(f"IMAP error: {e}")
        
        # Try API call again with fresh cookies from BD
        log("\n=== Python API call ===")
        rs = requests.Session()
        rs.proxies = {'http': BRD, 'https': BRD}
        rs.verify = False
        
        for name, value in cookie_dict.items():
            rs.cookies.set(name, value, domain='.cloudflare.com', path='/')
        
        r = rs.post(
            'https://dash.cloudflare.com/api/v4/user/create',
            data=req['body'],
            headers={k: v for k, v in req['headers'].items()},
            timeout=30
        )
        
        log(f"Status: {r.status_code}")
        try:
            data = r.json()
            log(f"Response: {json.dumps(data, indent=2)}")
        except:
            log(f"Response: {r.text[:300]}")
    
    browser.close()

log("=== Done ===")