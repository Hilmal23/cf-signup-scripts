#!/usr/bin/env python3
"""CF signup - intercept challenge + fetch clearance cookie"""
from camoufox import Camoufox
import time, re, json, http.server, threading, urllib.parse

PORT = 8765

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8', errors='ignore')
            log(f"PROXY POST: {self.path} | {body[:200]}")
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
        except:
            pass
    
    def log_message(self, *args): pass

def start_proxy():
    server = http.server.HTTPServer(('0.0.0.0', PORT), ProxyHandler)
    t = threading.Thread(target=lambda: server.serve_forever, daemon=True)
    t.start()
    return server

# Test: intercept CF challenge requests
log("=== Testing challenge interception ===")

server = start_proxy()
log(f"Proxy started on :{PORT}")

with Camoufox(headless=True, geoip=False) as browser:
    ctx = browser.new_context()
    page = ctx.new_page()
    
    # Intercept challenge requests
    challenge_requests = []
    
    def on_request(request):
        url = request.url
        if 'challenge' in url.lower() or 'turnstile' in url.lower() or 'jsd' in url.lower():
            challenge_requests.append({
                'url': url,
                'method': request.method,
                'headers': dict(request.headers),
                'post_data': request.post_data
            })
            log(f"CHALLENGE REQUEST: {request.method} {url[:100]}")
            log(f"  Headers: {dict(request.headers).get('Content-Type', 'no-ctype')}")
            log(f"  Post data: {str(request.post_data)[:200] if request.post_data else 'none'}")
    
    page.on_request(on_request)
    
    # Also intercept responses
    def on_response(response):
        url = response.url
        if 'challenge' in url.lower() or 'turnstile' in url.lower():
            log(f"CHALLENGE RESP: {response.status} {url[:100]}")
            try:
                headers = dict(response.headers)
                for h, v in headers.items():
                    if 'cf' in h.lower() or 'challenge' in h.lower():
                        log(f"  {h}: {v[:100]}")
            except: pass
    
    page.on_response(on_response)
    
    page.goto("https://dash.cloudflare.com/sign-up", timeout=30000)
    time.sleep(3)
    
    # Fill form
    page.fill('input[name="email"]', 'testproxy@hilmal.store')
    page.fill('input[name="password"]', 'ProxyTest123!')
    
    time.sleep(1)
    
    # Intercept all XHR
    log(f"Total challenge requests captured: {len(challenge_requests)}")
    
    # Check if any API calls are made
    for req in challenge_requests:
        log(f"  Request: {req['url'][:100]}")
        if 'post_data' in req and req['post_data']:
            log(f"    Data: {req['post_data'][:200]}")
    
    # Check cookies set by CF
    cookies = ctx.cookies()
    log(f"Cookies after form fill: {len(cookies)}")
    for c in cookies:
        if 'cf' in c['name'].lower() or 'challenge' in c['name'].lower():
            log(f"  {c['name']}: {c['value'][:50]}")
    
    page.screenshot(path='/tmp/cf_intercept.png')
    log("Screenshot saved!")
    
    browser.close()

server.shutdown()
log("=== Done ===")