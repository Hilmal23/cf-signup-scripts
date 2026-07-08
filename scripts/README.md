# CF Signup Scripts

## Free Turnstile Bypass Scripts

### cf_free_bypass.py
Tests multiple FREE approaches to bypass CF Turnstile:
- Test 1: No proxy (clean Kamatera IP)
- Test 2: Bright Data Web Unlocker proxy  
- Test 3: Dynamic Turnstile iframe detection
- Test 4: Direct API call (bypass browser)

### cf_camoufox_bypass.py
Uses Camoufox persistent profile to bypass Turnstile challenge.
Camoufox has anti-detection fingerprints that CF may trust,
allowing challenge pass WITHOUT explicit solving.

## Usage
```bash
python3 cf_free_bypass.py
python3 cf_camoufox_bypass.py
```

## Setup
```bash
pip install camoufox playwright cloudscraper
playwright install chromium
```
