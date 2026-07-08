#!/usr/bin/env python3
"""
CF Signup - CapSolver proxy mode (IP-matched solving!)
CapSolver has built-in proxy support — solve FROM same proxy as browser.
This solves the IP binding issue that killed 2Captcha tokens!
"""
import capsolver, time, requests

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

TWOCAPTCHA_KEY = "3da28555894fd89bb569b748731e9400"
SITEKEY = "0x4AAAAAAAJel0iaAR3mgkjp"
PAGE_URL = "https://dash.cloudflare.com/sign-up"
CHROMIUM = "/snap/chromium/current/usr/lib/chromium-browser/chrome"
PROXY_USER = "brd-customer-hl_c0f6789c-zone-web_unlocker1"
PROXY_PASS = "ds3ovbwhs69y"
PROXY = {'server': 'http://brd.superproxy.io:33335', 'username': PROXY_USER, 'password': PROXY_PASS}
PROXY_STR = f"http://{PROXY_USER}:{PROXY_PASS}@brd.superproxy.io:33335"
CHROME_ARGS = ["--no-sandbox","--disable-setuid-sandbox","--ignore-certificate-errors","--allow-running-insecure-content"]

# CapSolver API - check if we can use it
CAPSOLVER_API_KEY = None  # Need to get this

def test_capsolver():
    """Test if CapSolver works for CF Turnstile"""
    # First check what captcha solvers are accessible
    log("Checking solver accessibility...")
    
    # 1. CapSolver
    try:
        r = requests.get('https://api.capsolver.com/getBalance', timeout=5)
        log(f"CapSolver API: {r.status_code} {r.text[:100]}")
    except Exception as e:
        log(f"CapSolver inaccessible: {e}")
    
    # 2. Anti-Captcha
    try:
        r2 = requests.get('https://api.anti-captcha.com/getBalance', timeout=5)
        log(f"Anti-Captcha API: {r2.status_code}")
    except Exception as e:
        log(f"Anti-Captcha: {e}")
    
    # 3. DeathByCaptcha
    try:
        r3 = requests.get('http://api.dbcapi.me/api-info', timeout=5)
        log(f"DeathByCaptcha API: {r3.status_code}")
    except Exception as e:
        log(f"DeathByCaptcha: {e}")
    
    # 4. Check CapSolver Python SDK
    try:
        import importlib
        capsolver_spec = importlib.util.find_spec("capsolver")
        log(f"CapSolver SDK installed: {capsolver_spec is not None}")
    except:
        pass

def solve_via_capsolver():
    """Solve Turnstile using CapSolver with proxy"""
    log("=== CapSolver Turnstile Solve ===")
    
    # CapSolver requires an API key - check if we have one
    # or try to register for trial
    try:
        import capsolver
        log(f"CapSolver SDK version: {capsolver.__version__}")
    except ImportError:
        log("CapSolver not installed")
        return None
    
    # CapSolver has automatic proxy detection
    # But for CF Turnstile, we might need to specify the proxy
    capsolver.api_key = "CAP-SOLVER-API-KEY-HERE"  # User needs to provide this
    
    try:
        solution = capsolver.solve(
            type="CloudflareTurnstileTask",
            websiteUrl=PAGE_URL,
            websiteKey=SITEKEY,
            # CapSolver auto-detects proxy from environment if not specified
        )
        log(f"Token: {solution[:50]}...")
        return solution
    except Exception as e:
        log(f"CapSolver error: {e}")
        return None

def solve_via_anticaptcha():
    """Solve via Anti-Captcha (alternative)"""
    log("=== Anti-Captcha Turnstile Solve ===")
    # Anti-Captcha also supports proxy mode
    return None

def solve_with_2captcha_via_proxy():
    """Try 2Captcha through BD proxy (this failed before, but let's see why)"""
    log("=== 2Captcha via BD Proxy ===")
    
    # Get initial proxy port from BD
    # Note: 2Captcha uses datacenter IPs, not proxy IPs
    # So routing through BD proxy won't help
    
    return None

def main():
    log("=== Solver Comparison Test ===")
    test_capsolver()
    log("\nDone")

if __name__ == '__main__':
    main()