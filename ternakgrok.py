"""xAI console signup via API:
DARI AI UNTUK AI
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import random
import re
import string
import sys
import time
from urllib.parse import quote

from dotenv import load_dotenv
from curl_cffi import requests as cffi_requests
import requests as std_requests

load_dotenv()

# ── ANSI Colors ──────────────────────────────────────────────────────
class C:
    RESET   = "\033[0m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"

def ok(msg: str) -> str:
    return f"{C.GREEN}{msg}{C.RESET}"

def fail(msg: str) -> str:
    return f"{C.RED}{msg}{C.RESET}"

def warn(msg: str) -> str:
    return f"{C.YELLOW}{msg}{C.RESET}"

def info(msg: str) -> str:
    return f"{C.CYAN}{msg}{C.RESET}"

def step(msg: str) -> str:
    return f"{C.BLUE}{msg}{C.RESET}"

def bold(msg: str) -> str:
    return f"{C.BOLD}{msg}{C.RESET}"

def dim(msg: str) -> str:
    return f"{C.DIM}{msg}{C.RESET}"

# ── Config ───────────────────────────────────────────────────────────
BASE = "https://console.x.ai"
SEND_URL = f"{BASE}/api/auth/send-verification-code"
VERIFY_URL = f"{BASE}/api/auth/sign-up/verify-email"
CREATE_URL = f"{BASE}/api/auth/sign-up/create-account"

EMAIL_DOMAIN = "hungtpt.site"
GENERATOR_BASE = "https://generator.email"
DEFAULT_PASSWORD = os.getenv("DEFAULT_PASSWORD", "LauSapeEmpruy88@@")

TURNSTILE_SITEKEY = "0x4AAAAAAAhr9JGVDZbrZOo0"
TURNSTILE_PAGE_URL = f"{BASE}/login?mode=sign-up"
TURNSTILE_SOLVER_BASE = ""  # empty = use camoufox by default; set to solver URL to use external

ROUTER_BASE = "http://localhost:20128"
ROUTER_AUTH_TOKEN = os.getenv("ROUTER_AUTH_TOKEN", "")
OTP_FALSE_POSITIVE = {
    "FAFAFA", "ABCDEF", "123456", "000000", "111111", "989898",
    "FFFFFF", "AAAAAA", "QQQQQQ", "XXXXXX", "SCRIPT", "STYLE",
    "BUTTON", "OBJECT", "WINDOW", "DOCUMENT", "NUMBER", "STRING",
    "RETURN", "IMPORT", "EXPORT", "LENGTH", "SOURCE", "TARGET",
}

API_HEADERS = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "content-type": "application/json",
    "origin": BASE,
    "referer": f"{BASE}/login",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
}


FIRST_NAMES = [
    "Ahmad", "Rafi", "Dimas", "Budi", "Andi", "Sari", "Putri", "Dewi",
    "Agus", "Eka", "Rizky", "Fajar", "Bayu", "Yudi", "Tono", "Wawan",
    "Indah", "Rina", "Ayu", "Kartika", "Mega", "Nanda", "Citra", "Lestari",
    "Hendra", "Joko", "Taufik", "Arif", "Yusuf", "Nurul", "Fitri", "Melati",
    "Hani", "Dian", "Rizal", "Slamet", "Surya", "Galih", "Farhan", "Rizwan",
    "Sinta", "Maya", "Novi", "Rosa", "Yani", "Tia", "Dianita", "Rizka",
    "Rachma", "Anisa"
]

LAST_NAMES = [
    "Udin", "Pratama", "Saputra", "Wijaya", "Nugraha", "Santoso",
    "Hidayat", "Gunawan", "Susanto", "Mahendra", "Setiawan", "Firmansyah",
    "Syahputra", "Ramadhan", "Permana", "Sutrisno", "Wibowo", "Suryadi",
    "Kurniawan", "Subekti", "Suharto", "Basuki", "Purnomo", "Iskandar",
    "Halim", "Nasution", "Lubis", "Simanjuntak", "Hutagalung", "Siregar",
    "Manullang", "Sinaga", "Panjaitan", "Sitompul", "Tambunan", "Hutapea",
    "Ginting", "Tarigan", "Sembiring", "Purba", "Saragih", "Pakpahan",
    "Nainggolan", "Hutasoit", "Pasaribu", "Tobing", "Sihombing", "Malau",
    "LumbanGaol", "Hutajulu"
]

def random_email(domain: str = EMAIL_DOMAIN, length: int = 8) -> str:
    chars = string.ascii_lowercase + string.digits
    username = "".join(random.choices(chars, k=length))
    return f"{username}@{domain}"


def random_name() -> tuple[str, str]:
    return random.choice(FIRST_NAMES), random.choice(LAST_NAMES)


def parse_email(email: str) -> tuple[str, str]:
    if "@" not in email:
        raise ValueError(f"invalid email: {email}")
    user, domain = email.rsplit("@", 1)
    return user, domain


class TempEmail:
    def __init__(self, email: str, proxy: str | None = None):
        self.username, self.domain = parse_email(email)
        self.email = email
        self.session = std_requests.Session()
        self.proxies = {"http": proxy, "https": proxy} if proxy else None

    def _headers(self) -> dict:
        return {
            "user-agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/136.0.0.0 Safari/537.36"
            ),
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "accept-language": "en-US,en;q=0.9",
        }

    def warm(self) -> None:
        inbox_url = f"{GENERATOR_BASE}/{self.domain}/{self.username}"
        self.session.get(GENERATOR_BASE, headers=self._headers(), timeout=20, proxies=self.proxies)
        self.session.get(inbox_url, headers=self._headers(), timeout=20, proxies=self.proxies)

    def get_inbox_page(self) -> str:
        inbox_url = f"{GENERATOR_BASE}/{self.domain}/{self.username}"
        resp = self.session.get(
            inbox_url,
            headers=self._headers(),
            timeout=20,
            proxies=self.proxies,
        )
        return resp.text if resp.status_code == 200 else ""

    @staticmethod
    def _normalize_code(code: str) -> str:
        return code.strip().upper().replace("-", "").replace(" ", "")

    @staticmethod
    def _is_plausible_code(code: str) -> bool:
        """xAI email codes are always 6 alnum after removing dash, e.g. CMF-EAX -> CMFEAX."""
        c = TempEmail._normalize_code(code)
        if len(c) != 6 or not c.isalnum():
            return False
        if c in OTP_FALSE_POSITIVE:
            return False
        if c.startswith("20"):
            return False
        # reject pure words / pure junk; allow all-letter codes like CMFEAX
        if c.isalpha() and c in OTP_FALSE_POSITIVE:
            return False
        if len(set(c)) <= 2:
            return False
        return True

    @staticmethod
    def _strip_noise(html: str) -> str:
        html = re.sub(r"(?is)<script\b[^>]*>.*?</script>", " ", html)
        html = re.sub(r"(?is)<style\b[^>]*>.*?</style>", " ", html)
        html = re.sub(r"(?is)<!--.*?-->", " ", html)
        return html

    def extract_code(self, text: str) -> str | None:
        """Only accept codes from the actual xAI confirmation email subject.

        Real subject example:
          SpaceXAI confirmation code: CMF-EAX
        Never scan random page tokens (PER100, SCRIPT, CSS crumbs, ads).
        """
        if not text:
            return None

        text = self._strip_noise(text)

        # 1) exact confirmation/verification subject patterns (dashed preferred)
        patterns = [
            r"SpaceXAI\s+confirmation code[:\s]+([A-Z0-9]{3}-[A-Z0-9]{3})",
            r"confirmation code[:\s]+([A-Z0-9]{3}-[A-Z0-9]{3})",
            r"verification code[:\s]+([A-Z0-9]{3}-[A-Z0-9]{3})",
            r"SpaceXAI\s+confirmation code[:\s]+([A-Z0-9]{6})",
            r"confirmation code[:\s]+([A-Z0-9]{6})",
            r"verification code[:\s]+([A-Z0-9]{6})",
        ]
        for pat in patterns:
            matches = re.findall(pat, text, re.IGNORECASE)
            for m in reversed(matches):
                if self._is_plausible_code(m):
                    return self._normalize_code(m)

        # 2) generator.email subject div only
        for block in re.findall(
            r'class="[^"]*subj_div[^"]*"[^>]*>(.*?)</div>',
            text,
            re.IGNORECASE | re.DOTALL,
        ):
            m = re.search(
                r"(?:confirmation|verification)\s+code[:\s]+([A-Z0-9]{3}-[A-Z0-9]{3}|[A-Z0-9]{6})",
                block,
                re.I,
            )
            if m and self._is_plausible_code(m.group(1)):
                return self._normalize_code(m.group(1))
            # subject is literally just the code form
            m = re.search(r"\b([A-Z0-9]{3}-[A-Z0-9]{3})\b", block, re.I)
            if m and self._is_plausible_code(m.group(1)):
                return self._normalize_code(m.group(1))

        # Do NOT scan whole HTML for bare 6-char tokens (caused PER100/SCRIPT)
        return None

    def wait_for_code(self, max_retries: int = 25, delay: int = 4) -> str | None:
        for attempt in range(1, max_retries + 1):
            try:
                code = self.extract_code(self.get_inbox_page())
            except Exception as e:
                print(f"  {warn('...')} inbox error ({attempt}/{max_retries}): {fail(str(e))}")
                code = None
            if code:
                print()  # finish the waiting line cleanly
                return code
            if attempt < max_retries:
                print(f"  {warn('...')} waiting OTP ({attempt}/{max_retries})   ", end="\r", flush=True)
                time.sleep(delay)
        print()
        return None


def make_session(impersonate: str, proxy: str | None) -> cffi_requests.Session:
    session = cffi_requests.Session(impersonate=impersonate)
    if proxy:
        session.proxies = {"http": proxy, "https": proxy}
    return session


def warmup(session: cffi_requests.Session) -> None:
    session.get(
        f"{BASE}/login",
        headers={
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "accept-language": "en-US,en;q=0.9",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
        },
        timeout=30,
        allow_redirects=True,
    )


def send_code(session: cffi_requests.Session, email: str) -> cffi_requests.Response:
    return session.post(SEND_URL, headers=API_HEADERS, json={"email": email}, timeout=30)


def verify_email(session: cffi_requests.Session, email: str, code: str) -> cffi_requests.Response:
    return session.post(
        VERIFY_URL,
        headers=API_HEADERS,
        json={"email": email, "code": code},
        timeout=30,
    )


def create_account(
    session: cffi_requests.Session,
    email: str,
    password: str,
    given_name: str,
    family_name: str,
    email_code: str,
    turnstile_token: str,
) -> cffi_requests.Response:
    payload = {
        "email": email,
        "password": password,
        "givenName": given_name,
        "familyName": family_name,
        "emailValidationCode": email_code,
        "turnstileToken": turnstile_token,
    }
    return session.post(CREATE_URL, headers=API_HEADERS, json=payload, timeout=45)


def solve_turnstile_camoufox(
    sitekey: str = TURNSTILE_SITEKEY,
    page_url: str = TURNSTILE_PAGE_URL,
    proxy: str | None = None,
    timeout_ms: int = 60_000,
) -> str:
    """Solve Turnstile using camoufox headless browser (no external API needed)."""
    from camoufox.sync_api import Camoufox

    launch_kw: dict = {"headless": True}
    if proxy:
        from urllib.parse import urlparse
        p = urlparse(proxy)
        pcfg: dict = {"server": f"{p.scheme}://{p.hostname}:{p.port}"}
        if p.username:
            pcfg["username"] = p.username
        if p.password:
            pcfg["password"] = p.password
        launch_kw["proxy"] = pcfg
        launch_kw["geoip"] = True

    token = None
    with Camoufox(**launch_kw) as browser:
        page = browser.new_page()

        # Inject hook SEBELUM page load - tangkap token dari turnstile callback
        # add_script_tag inject ke DOM, bukan eval, jadi lolos CSP
        hook_js = """
        (function() {
            window.__turnstile_token = null;
            // Hook turnstile.render untuk capture callback
            const checkTurnstile = setInterval(function() {
                if (window.turnstile && window.turnstile.render) {
                    clearInterval(checkTurnstile);
                    const origRender = window.turnstile.render;
                    window.turnstile.render = function(container, opts) {
                        const origCallback = opts.callback;
                        opts.callback = function(token) {
                            window.__turnstile_token = token;
                            if (origCallback) origCallback(token);
                        };
                        return origRender.call(this, container, opts);
                    };
                    // Juga auto-render turnstile widget
                    try {
                        const div = document.createElement('div');
                        div.className = 'cf-turnstile';
                        div.style.display = 'none';
                        document.body.appendChild(div);
                        window.turnstile.render(div, {
                            sitekey: '%s',
                            callback: function(t) { window.__turnstile_token = t; }
                        });
                    } catch(e) {}
                }
            }, 100);
        })();
        """ % sitekey

        page.add_init_script(hook_js)
        page.goto(page_url, wait_until="networkidle", timeout=30_000)

        # Tunggu token dari hook
        deadline = time.time() + (timeout_ms / 1000)
        while time.time() < deadline:
            try:
                # page.content() tidak pakai eval, lolos CSP
                html = page.content()
                # Cek apakah token ada di context via console message
                # Atau cek di response header/cookie
            except Exception:
                pass

            # Coba ambil token via console log
            try:
                # Inject script kecil yang print token ke console
                check_script = """
                (function() {
                    if (window.__turnstile_token) {
                        console.log('TURNSTILE_TOKEN:' + window.__turnstile_token);
                    }
                })();
                """
                page.add_script_tag(content=check_script)
            except Exception:
                pass

            time.sleep(1)

        # Intercept console messages untuk ambil token
        captured_console = []
        page.on("console", lambda msg: captured_console.append(msg.text) if "TURNSTILE_TOKEN:" in msg.text else None)

        # Re-inject check setelah hook
        try:
            check_script = """
            (function() {
                if (window.__turnstile_token) {
                    console.log('TURNSTILE_TOKEN:' + window.__turnstile_token);
                }
            })();
            """
            page.add_script_tag(content=check_script)
        except Exception:
            pass

        time.sleep(2)

        # Parse token dari console
        for msg in captured_console:
            if "TURNSTILE_TOKEN:" in msg:
                token = msg.split("TURNSTILE_TOKEN:")[1].strip()
                break

        # Fallback: cek network response untuk turnstile verify
        if not token:
            try:
                html = page.content()
                # Cari token di script tags
                import re as _re
                match = _re.search(r'turnstile.*?token["\s:=]+["\']([a-zA-Z0-9._-]{100,})["\']', html)
                if match:
                    token = match.group(1)
            except Exception:
                pass

    if not token or len(token) < 40:
        raise RuntimeError(f"camoufox turnstile bad token: {token!r}")
    return token


def solve_turnstile(
    sitekey: str = TURNSTILE_SITEKEY,
    page_url: str = TURNSTILE_PAGE_URL,
    solver_base: str = TURNSTILE_SOLVER_BASE,
    max_wait: int = 180,
    poll_every: float = 2.0,
    proxy: str | None = None,
) -> str:
    """Try external solver first; fall back to camoufox if it fails/times out."""
    # ── camoufox direct (no external solver) ──────────────────────────
    if not solver_base:
        return solve_turnstile_camoufox(sitekey=sitekey, page_url=page_url, proxy=proxy)

    # ── external solver ──────────────────────────────────────────────
    create_url = (
        f"{solver_base.rstrip('/')}/turnstile"
        f"?url={quote(page_url, safe='')}"
        f"&sitekey={quote(sitekey, safe='')}"
    )
    try:
        create_resp = std_requests.get(create_url, timeout=15)
        create_resp.raise_for_status()
        create_data = create_resp.json()
    except Exception:
        return solve_turnstile_camoufox(sitekey=sitekey, page_url=page_url, proxy=proxy)

    task_id = create_data.get("task_id") or create_data.get("id")
    if not task_id:
        return solve_turnstile_camoufox(sitekey=sitekey, page_url=page_url, proxy=proxy)

    result_url = f"{solver_base.rstrip('/')}/result?id={quote(str(task_id), safe='')}"
    deadline = time.time() + max_wait
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        try:
            resp = std_requests.get(result_url, timeout=15)
        except Exception:
            time.sleep(poll_every)
            continue
        text = resp.text.strip()
        try:
            data = resp.json()
        except Exception:
            data = None

        token = None
        status = None
        if isinstance(data, dict):
            status = str(data.get("status", "")).lower()
            nested = data.get("data")
            nested_token = None
            if isinstance(nested, dict):
                nested_token = nested.get("token") or nested.get("value") or nested.get("result")
            elif isinstance(nested, str):
                nested_token = nested
            token = (
                data.get("token")
                or data.get("turnstileToken")
                or data.get("value")
                or data.get("result")
                or nested_token
            )
            if isinstance(token, dict):
                token = token.get("token") or token.get("value")
        elif isinstance(data, str) and len(data) > 40:
            token = data
        elif text and "status" not in text.lower() and len(text) > 40 and " " not in text:
            token = text.strip('"')

        if token and isinstance(token, str) and len(token) > 40:
            return token

        if status in {"failed", "error", "fail"}:
            return solve_turnstile_camoufox(sitekey=sitekey, page_url=page_url, proxy=proxy)

        time.sleep(poll_every)

    return solve_turnstile_camoufox(sitekey=sitekey, page_url=page_url, proxy=proxy)


def print_resp(label: str, resp: cffi_requests.Response, verbose: bool = False) -> None:
    body = resp.text
    ok_status = resp.status_code < 400
    if "cloudflare" in body.lower() and len(body) > 400:
        tag = "BLOCKED" if "Sorry, you have been blocked" in body else "CF-HTML"
        print(f"  {fail('[BLOCKED]')} [{label}] {resp.status_code} {warn(tag)}")
        return
    if verbose or not ok_status:
        try:
            j = resp.json()
            print(f"  {fail('[ERR]')} [{label}] {resp.status_code} {dim(json.dumps(j))}")
        except Exception:
            print(f"  {fail('[ERR]')} [{label}] {resp.status_code} {dim(body[:300])}")
    else:
        print(f"  {ok('[OK]')} [{label}] {resp.status_code} {ok('ok')}")


def connect_to_router(
    page,
    router_base: str = ROUTER_BASE,
    router_token: str = ROUTER_AUTH_TOKEN,
) -> bool:
    """Authorize new xAI account to 9router via browser."""
    _safe_print(f"  {info('[+]')} Menghubungkan ke {bold('9router')}...")

    # Step 1: Get device code from 9router
    try:
        resp = std_requests.get(
            f"{router_base}/api/oauth/grok-cli/device-code",
            cookies={"auth_token": router_token},
            headers={"Accept": "*/*"},
            timeout=15,
        )
        if resp.status_code != 200:
            _safe_print(f"  {fail('[ERR]')} 9router tidak merespons (kode {resp.status_code})")
            return False
        data = resp.json()
        _safe_print(f"  {dim('[debug]')} Device code: {str(data)[:200]}")
    except Exception as e:
        _safe_print(f"  {fail('[ERR]')} 9router tidak dapat dijangkau: {e}")
        return False

    device_code = data.get("device_code") or data.get("deviceCode")
    code_verifier = data.get("codeVerifier") or data.get("code_verifier")
    user_code = data.get("user_code") or data.get("userCode")
    verify_url = data.get("verification_uri_complete") or data.get("verificationUriComplete")

    _safe_print(f"  {dim('[debug]')} verify_url: {verify_url}")
    _safe_print(f"  {dim('[debug]')} user_code: {user_code}")

    if not verify_url:
        _safe_print(f"  {fail('[ERR]')} URL verifikasi tidak ditemukan")
        return False

    # Step 2: Navigate to verification URL in browser
    try:
        _safe_print(f"  {dim('[debug]')} Navigating to verify URL...")
        page.goto(verify_url, wait_until="networkidle", timeout=15_000)
        time.sleep(2)

        _safe_print(f"  {dim('[debug]')} Page URL: {page.url}")

        # Dismiss cookie banner if exists
        try:
            page.locator('#onetrust-accept-btn-handler').click(timeout=2_000)
            time.sleep(0.5)
        except Exception:
            pass

        # Click "Continue" button
        continue_btn = page.locator('button:has-text("Continue"), button:has-text("Allow")')
        _safe_print(f"  {dim('[debug]')} Continue buttons: {continue_btn.count()}")
        if continue_btn.count() > 0:
            btn_text = continue_btn.first.inner_text()
            _safe_print(f"  {dim('[debug]')} Clicking: {btn_text}")
            continue_btn.first.click()
            time.sleep(3)

        # Click "Allow" button if appears
        allow_btn = page.locator('button:has-text("Allow"), button:has-text("Authorize")')
        _safe_print(f"  {dim('[debug]')} Allow buttons: {allow_btn.count()}")
        if allow_btn.count() > 0:
            btn_text = allow_btn.first.inner_text()
            _safe_print(f"  {dim('[debug]')} Clicking: {btn_text}")
            allow_btn.first.click()
            time.sleep(3)

        _safe_print(f"  {dim('[debug]')} Final URL: {page.url}")
    except Exception as e:
        _safe_print(f"  {fail('[ERR]')} Gagal verifikasi browser: {e}")
        return False

    # Step 3: Poll 9router
    try:
        _safe_print(f"  {dim('[debug]')} Polling 9router...")
        poll_resp = std_requests.post(
            f"{router_base}/api/oauth/grok-cli/poll",
            json={"deviceCode": device_code, "codeVerifier": code_verifier, "extraData": None},
            cookies={"auth_token": router_token},
            headers={"Accept": "*/*", "Content-Type": "application/json"},
            timeout=15,
        )
        _safe_print(f"  {dim('[debug]')} Poll response: {poll_resp.status_code} {poll_resp.text[:200]}")
        if poll_resp.status_code == 200:
            try:
                poll_data = poll_resp.json()
                if poll_data.get("success"):
                    _safe_print(f"  {ok('[OK]')} Akun terhubung ke {bold('9router')}!")
                    return True
                else:
                    _safe_print(f"  {fail('[ERR]')} 9router tolak: {poll_data.get('error', 'unknown')} - {poll_data.get('errorDescription', '')}")
                    return False
            except Exception:
                _safe_print(f"  {fail('[ERR]')} Response tidak valid: {poll_resp.text[:100]}")
                return False
        else:
            _safe_print(f"  {fail('[ERR]')} Poll gagal: {dim(poll_resp.text[:200])}")
            return False
    except Exception as e:
        _safe_print(f"  {fail('[ERR]')} Poll error: {e}")
        return False


import threading as _threading
import datetime as _dt


def _print_lock_fn():
    """Return a module-level print lock (created once)."""
    if not hasattr(_print_lock_fn, "_lock"):
        _print_lock_fn._lock = _threading.Lock()
    return _print_lock_fn._lock


def _safe_print(*a, **kw):
    with _print_lock_fn():
        print(*a, **kw)


def register_one(args, worker_id: int = 0) -> bool:
    """Buat satu akun via browser. Return True jika berhasil."""
    prefix = f"{dim(f'[#{worker_id}]')}" if worker_id else ""

    email = random_email()
    username, domain = email.split("@")
    given_name = random.choice(FIRST_NAMES)
    family_name = random.choice(LAST_NAMES)

    _safe_print(f"\n{prefix} {step('➤')} {bold(email)}  - {given_name} {family_name}")

    # inbox warmup
    mail = TempEmail(email, proxy=None)
    try:
        mail.warm()
    except Exception:
        pass

    # ── Browser flow ─────────────────────────────────────────────────
    from camoufox.sync_api import Camoufox

    launch_kw: dict = {"headless": True}
    if args.proxy:
        from urllib.parse import urlparse
        p = urlparse(args.proxy)
        pcfg: dict = {"server": f"{p.scheme}://{p.hostname}:{p.port}"}
        if p.username:
            pcfg["username"] = p.username
        if p.password:
            pcfg["password"] = p.password
        launch_kw["proxy"] = pcfg
        launch_kw["geoip"] = True

    try:
        with Camoufox(**launch_kw) as browser:
            page = browser.new_page()

            # 1) Navigate to sign-up
            _safe_print(f"{prefix}  {step('[1/5]')} {warn('Membuka halaman sign-up...')}")
            page.goto("https://accounts.x.ai/sign-up", wait_until="networkidle", timeout=30_000)
            time.sleep(2)

            # Dismiss cookie banner jika ada
            try:
                cookie_btn = page.locator('#onetrust-accept-btn-handler')
                if cookie_btn.count() > 0:
                    cookie_btn.click(timeout=3_000)
                    time.sleep(1)
            except Exception:
                pass

            # 2) Click "Sign up with email"
            _safe_print(f"{prefix}  {dim('[debug]')} URL: {page.url}")
            page.click("text=Sign up with email", timeout=10_000)
            time.sleep(2)

            # 3) Fill email & submit
            page.fill('input[type="email"]', email)
            time.sleep(0.5)
            page.click('button[type="submit"]', timeout=10_000)
            time.sleep(3)
            _safe_print(f"{prefix}  {dim('[debug]')} URL after submit: {page.url}")
            _safe_print(f"{prefix}  {step('[2/5]')} {ok('Email terkirim,')} {warn('menunggu OTP...')}")

            # 4) Wait for OTP
            code = mail.wait_for_code(max_retries=args.otp_retries, delay=args.otp_delay)
            if not code:
                _safe_print(f"{prefix}  {fail('[ERR]')} Kode OTP tidak diterima")
                return False
            _safe_print(f"{prefix}  {step('[3/5]')} {ok('OTP diterima:')} {bold(code)}")

            # 5) Enter OTP
            otp_input = page.locator('input[name="code"]')
            _safe_print(f"{prefix}  {dim('[debug]')} OTP input count: {otp_input.count()}")
            if otp_input.count() == 0:
                _safe_print(f"{prefix}  {fail('[ERR]')} Input OTP tidak ditemukan")
                return False
            otp_input.fill(code)
            time.sleep(0.5)
            page.click('button[type="submit"]', timeout=5_000)
            time.sleep(5)
            _safe_print(f"{prefix}  {dim('[debug]')} URL after OTP: {page.url}")

            # 6) Fill password
            pwd_input = page.locator('input[type="password"]')
            _safe_print(f"{prefix}  {dim('[debug]')} Password input count: {pwd_input.count()}")
            if pwd_input.count() > 0:
                pwd_input.first.fill(args.password)
                time.sleep(0.5)
                # Confirm password jika ada 2 input
                if pwd_input.count() > 1:
                    pwd_input.nth(1).fill(args.password)
                page.click('button[type="submit"]', timeout=5_000)
                time.sleep(5)
                _safe_print(f"{prefix}  {dim('[debug]')} URL after password: {page.url}")

            # 7) Fill name
            fname_input = page.locator('input[name="firstName"], input[autocomplete="given-name"]')
            lname_input = page.locator('input[name="lastName"], input[autocomplete="family-name"]')
            _safe_print(f"{prefix}  {dim('[debug]')} Name input count: {fname_input.count()}")
            if fname_input.count() > 0:
                fname_input.fill(given_name)
                lname_input.fill(family_name)
                time.sleep(0.5)
                page.click('button[type="submit"]', timeout=5_000)
                time.sleep(5)
                _safe_print(f"{prefix}  {dim('[debug]')} URL after name: {page.url}")

            # 8) Check success
            _safe_print(f"{prefix}  {step('[4/5]')} {ok('Proses selesai,')} {warn('cek status...')}")

            # Get cookies
            cookies = page.context.cookies()
            session_cookies = {c["name"]: c["value"] for c in cookies}
            _safe_print(f"{prefix}  {dim('[debug]')} Cookies: {list(session_cookies.keys())}")

            # Check for sso cookie (indicates success)
            uid = "-"
            if "sso" in session_cookies or "sso-rw" in session_cookies:
                _safe_print(f"{prefix}  {ok('[OK]')} {ok('Akun berhasil dibuat!')}")
                # Extract user ID from sso cookie
                try:
                    sso_val = session_cookies.get("sso") or session_cookies.get("sso-rw")
                    if sso_val:
                        parts = sso_val.split(".")
                        if len(parts) >= 2:
                            payload = parts[1] + "=" * (4 - len(parts[1]) % 4)
                            decoded = base64.b64decode(payload).decode()
                            data = json.loads(decoded)
                            uid = data.get("sub", data.get("user_id", data.get("session_id", "-")))
                            _safe_print(f"{prefix}  {dim('[debug]')} SSO data: {data}")
                except Exception as e:
                    _safe_print(f"{prefix}  {dim('[debug]')} SSO decode error: {e}")

                # Fallback: get uid from console page
                if uid == "-":
                    try:
                        page.goto("https://console.x.ai", wait_until="networkidle", timeout=15_000)
                        time.sleep(2)
                        html = page.content()
                        uid_match = re.search(r'"userId"[:\s]+"([^"]+)"', html)
                        if uid_match:
                            uid = uid_match.group(1)
                    except Exception:
                        pass
            else:
                _safe_print(f"{prefix}  {fail('[ERR]')} Akun gagal dibuat (cookies: {list(session_cookies.keys())})")
                return False

            # 9) Connect to 9router
            router_status = "-"
            if args.router:
                ok_router = connect_to_router(
                    page=page,
                    router_base=args.router_base,
                    router_token=args.router_token,
                )
                router_status = "connected" if ok_router else "failed"

    except Exception as e:
        _safe_print(f"{prefix}  {fail('[ERR]')} Browser error: {fail(str(e))}")
        return False

    # simpan ke accounts.txt
    ts = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{email}|{args.password}|{given_name} {family_name}|{uid}|router={router_status}|{ts}\n"
    with _print_lock_fn():
        with open("accounts.txt", "a", encoding="utf-8") as f:
            f.write(line)
    _safe_print(f"{prefix}  {step('[5/5]')} {ok('Tersimpan')} {step('➤')} {bold('accounts.txt')}")
    return True


def main() -> int:
    args = argparse.Namespace(
        email=None,
        proxy=None,
        impersonate="chrome136",
        password=DEFAULT_PASSWORD,
        given_name=None,
        family_name=None,
        code=None,
        turnstile_token=None,
        solver=TURNSTILE_SOLVER_BASE,
        sitekey=TURNSTILE_SITEKEY,
        no_warmup=False,
        send_only=False,
        verify_only=False,
        otp_retries=25,
        otp_delay=4,
        turnstile_wait=180,
        router=True,
        router_token=ROUTER_AUTH_TOKEN,
        router_base=ROUTER_BASE,
        verbose=False,
        count=None,
        threads=None,
    )

    # Tanya interaktif jika tidak di-pass via argumen
    if args.count is None:
        try:
            args.count = int(input(f"{info('?')} Berapa banyak akun yang ingin dibuat? "))
        except (ValueError, EOFError):
            args.count = 1
    if args.threads is None:
        try:
            args.threads = int(input(f"{info('?')} Berapa thread (proses paralel)? [1 = satu-satu] "))
        except (ValueError, EOFError):
            args.threads = 1
    if args.proxy is None:
        try:
            pakai = input(f"{info('?')} Mau pakai proxy? (y/n) ").strip().lower()
            if pakai == "y":
                args.proxy = input(f"{info('?')} Masukkan proxy (http://user:pass@host:port): ").strip() or None
        except EOFError:
            pass

    args.count = max(1, args.count)
    args.threads = max(1, min(args.threads, args.count))

    print(f"\n {step('➤')} Membuat {bold(str(args.count))} akun dengan {bold(str(args.threads))} thread...")
    print(f"{dim('=' * 46)}")

    results = {"ok": 0, "fail": 0}
    lock = _threading.Lock()
    start_time = _dt.datetime.now()

    def worker(wid: int):
        result = register_one(args, worker_id=wid)
        with lock:
            if result:
                results["ok"] += 1
            else:
                results["fail"] += 1

    # Jalankan dengan thread pool
    pending = list(range(1, args.count + 1))
    while pending:
        batch = pending[: args.threads]
        pending = pending[args.threads :]
        threads = [_threading.Thread(target=worker, args=(wid,), daemon=True) for wid in batch]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    elapsed = _dt.datetime.now() - start_time
    total_sec = int(elapsed.total_seconds())
    menit, detik = divmod(total_sec, 60)

    print(f"\n{dim('=' * 46)}")
    print(f" {ok('[OK]')} Berhasil : {ok(str(results['ok']))}")
    if results["fail"]:
        print(f" {fail('[ERR]')} Gagal    : {fail(str(results['fail']))}")
    print(f" {info('[i]')} Waktu    : {bold(f'{menit} menit {detik} detik')}")
    print(f" {step('➤')} Lihat akun di: {bold('accounts.txt')}")
    return 0 if results["fail"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
