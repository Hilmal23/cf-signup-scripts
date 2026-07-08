#!/usr/bin/env python3
import requests, re, sys

r = requests.get('https://dash.cloudflare.com/sign-up', 
    headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'},
    timeout=15)
html = r.text

# Find API scripts
scripts = re.findall(r'<script[^>]*src="([^"]*api\.js[^"]*)"', html)
print(f'API scripts: {len(scripts)}')
for s in scripts:
    print(f'  {s[:120]}')

# Find sitekey
sitekeys = re.findall(r'data-sitekey="([^"]+)"', html)
print(f'data-sitekey: {sitekeys}')

# Check for rendered turnstile div
ts = re.findall(r'data-cf.*sitekey.*?["\']([^"\']+)["\']', html)
print(f'CF sitekey: {ts}')

# Look for sitekey in any context
sk = re.findall(r'sitekey["\s:=]+[^"\']*["\']([a-zA-Z0-9_-]{20,})["\']', html)
print(f'Generic sitekey: {sk[:5]}')

# Check the script tags that load turnstile
for script in scripts:
    if 'turnstile' in script.lower():
        print(f'Turnstile script: {script[:120]}')
        # Fetch the script URL and search for sitekey
        try:
            sr = requests.get(script, timeout=10)
            # Look for sitekey in the script
            found = re.findall(r'["\']sitekey["\']\s*:\s*["\']([^"\']{20,})["\']', sr.text)
            found2 = re.findall(r'sitekey["\s:=]+["\']([a-zA-Z0-9_-]{20,})["\']', sr.text)
            print(f'  Found in script: {found[:3]}')
            print(f'  Found2 in script: {found2[:3]}')
        except:
            pass

print(f'\nHTML length: {len(html)}')