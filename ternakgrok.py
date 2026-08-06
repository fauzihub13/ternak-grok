"""xAI auto register + connect 9router. Headless Camoufox + curl_cffi only."""

from __future__ import annotations

import base64
import datetime as _dt
import json
import os
import random
import re
import string
import sys
import threading as _threading
import time

from curl_cffi import requests as cffi_requests
from dotenv import load_dotenv
import requests as std_requests

load_dotenv()

# ── Colors ───────────────────────────────────────────────────────────
class C:
    R = "\033[0m"
    RED = "\033[91m"
    GRN = "\033[92m"
    YEL = "\033[93m"
    BLU = "\033[94m"
    CYN = "\033[96m"
    BLD = "\033[1m"
    DIM = "\033[2m"


def ok(m: str) -> str:
    return f"{C.GRN}{m}{C.R}"


def err(m: str) -> str:
    return f"{C.RED}{m}{C.R}"


def warn(m: str) -> str:
    return f"{C.YEL}{m}{C.R}"


def info(m: str) -> str:
    return f"{C.CYN}{m}{C.R}"


def step(m: str) -> str:
    return f"{C.BLU}{m}{C.R}"


def bold(m: str) -> str:
    return f"{C.BLD}{m}{C.R}"


def dim(m: str) -> str:
    return f"{C.DIM}{m}{C.R}"


# ── Config ───────────────────────────────────────────────────────────
GENERATOR_BASE = "https://generator.email"
DEFAULT_PASSWORD = os.getenv("DEFAULT_PASSWORD", "LauSapeEmpruy88@@")
ROUTER_BASE = os.getenv("ROUTER_BASE", "http://localhost:20128")
ROUTER_AUTH_TOKEN = os.getenv("ROUTER_AUTH_TOKEN", "")
EMAIL_DOMAINS = [
    d.strip()
    for d in os.getenv("EMAIL_DOMAINS", "hungtpt.site").split(",")
    if d.strip()
]

OTP_FALSE = {
    "FAFAFA", "ABCDEF", "123456", "000000", "111111", "989898",
    "FFFFFF", "AAAAAA", "QQQQQQ", "XXXXXX", "SCRIPT", "STYLE",
    "BUTTON", "OBJECT", "WINDOW", "DOCUMENT", "NUMBER", "STRING",
    "RETURN", "IMPORT", "EXPORT", "LENGTH", "SOURCE", "TARGET",
}

FIRST_NAMES = [
    "Ahmad", "Rafi", "Dimas", "Budi", "Andi", "Sari", "Putri", "Dewi",
    "Agus", "Eka", "Rizky", "Fajar", "Bayu", "Yudi", "Tono", "Wawan",
    "Indah", "Rina", "Ayu", "Kartika", "Mega", "Nanda", "Citra", "Lestari",
    "Hendra", "Joko", "Taufik", "Arif", "Yusuf", "Nurul", "Fitri", "Melati",
    "Hani", "Dian", "Rizal", "Slamet", "Surya", "Galih", "Farhan", "Rizwan",
    "Sinta", "Maya", "Novi", "Rosa", "Yani", "Tia", "Dianita", "Rizka",
    "Rachma", "Anisa",
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
    "LumbanGaol", "Hutajulu",
]

_print_lock = _threading.Lock()


def _print(*a, **kw):
    with _print_lock:
        print(*a, **kw)


def random_email(length: int = 8) -> str:
    chars = string.ascii_lowercase + string.digits
    user = "".join(random.choices(chars, k=length))
    return f"{user}@{random.choice(EMAIL_DOMAINS)}"


# ── Temp email / OTP ─────────────────────────────────────────────────
class TempEmail:
    def __init__(self, email: str):
        self.username, self.domain = email.rsplit("@", 1)
        self.email = email
        self.session = std_requests.Session()
        self.headers = {
            "user-agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/136.0.0.0 Safari/537.36"
            ),
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

    def warm(self) -> None:
        inbox = f"{GENERATOR_BASE}/{self.domain}/{self.username}"
        try:
            self.session.get(GENERATOR_BASE, headers=self.headers, timeout=15)
            self.session.get(inbox, headers=self.headers, timeout=15)
        except Exception:
            pass

    def _inbox(self) -> str:
        url = f"{GENERATOR_BASE}/{self.domain}/{self.username}"
        try:
            r = self.session.get(url, headers=self.headers, timeout=15)
            return r.text if r.status_code == 200 else ""
        except Exception:
            return ""

    @staticmethod
    def _norm(code: str) -> str:
        return code.strip().upper().replace("-", "").replace(" ", "")

    @staticmethod
    def _ok(code: str) -> bool:
        c = TempEmail._norm(code)
        if len(c) != 6 or not c.isalnum() or c in OTP_FALSE:
            return False
        if c.startswith("20") or len(set(c)) <= 2:
            return False
        return True

    def extract(self, html: str) -> str | None:
        if not html:
            return None
        html = re.sub(r"(?is)<script\b[^>]*>.*?</script>", " ", html)
        html = re.sub(r"(?is)<style\b[^>]*>.*?</style>", " ", html)
        pats = [
            r"SpaceXAI\s+confirmation code[:\s]+([A-Z0-9]{3}-[A-Z0-9]{3})",
            r"confirmation code[:\s]+([A-Z0-9]{3}-[A-Z0-9]{3})",
            r"verification code[:\s]+([A-Z0-9]{3}-[A-Z0-9]{3})",
            r"SpaceXAI\s+confirmation code[:\s]+([A-Z0-9]{6})",
            r"confirmation code[:\s]+([A-Z0-9]{6})",
            r"verification code[:\s]+([A-Z0-9]{6})",
        ]
        for pat in pats:
            for m in reversed(re.findall(pat, html, re.I)):
                if self._ok(m):
                    return self._norm(m)
        for block in re.findall(
            r'class="[^"]*subj_div[^"]*"[^>]*>(.*?)</div>',
            html,
            re.I | re.S,
        ):
            m = re.search(
                r"(?:confirmation|verification)\s+code[:\s]+([A-Z0-9]{3}-[A-Z0-9]{3}|[A-Z0-9]{6})",
                block,
                re.I,
            )
            if m and self._ok(m.group(1)):
                return self._norm(m.group(1))
            m = re.search(r"\b([A-Z0-9]{3}-[A-Z0-9]{3})\b", block, re.I)
            if m and self._ok(m.group(1)):
                return self._norm(m.group(1))
        return None

    def wait_code(self, retries: int = 20, delay: float = 3) -> str | None:
        for i in range(1, retries + 1):
            code = self.extract(self._inbox())
            if code:
                print()
                return code
            if i < retries:
                print(f"  {warn('...')} OTP ({i}/{retries})   ", end="\r", flush=True)
                time.sleep(delay)
        print()
        return None


# ── curl_cffi helpers ────────────────────────────────────────────────
def make_session(proxy: str | None = None) -> cffi_requests.Session:
    s = cffi_requests.Session(impersonate="chrome136")
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}
    return s


def cookies_to_dict(page_cookies: list) -> dict:
    # Ambil semua cookie — jangan filter domain ketat (sso kadang domain beda)
    return {c["name"]: c["value"] for c in page_cookies}


def extract_uid(cookies: dict) -> str:
    for key in ("sso", "sso-rw"):
        val = cookies.get(key)
        if not val:
            continue
        try:
            parts = val.split(".")
            if len(parts) < 2:
                continue
            payload = parts[1] + "=" * (4 - len(parts[1]) % 4)
            data = json.loads(base64.b64decode(payload).decode())
            return data.get("sub") or data.get("user_id") or data.get("session_id") or "-"
        except Exception:
            continue
    return "-"


# ── 9router OAuth (curl_cffi + cookies) ──────────────────────────────
def connect_to_router(
    cookies: dict,
    router_base: str = ROUTER_BASE,
    router_token: str = ROUTER_AUTH_TOKEN,
    proxy: str | None = None,
    poll_retries: int = 5,
) -> bool:
    _print(f"  {info('[+]')} Connect 9router...")
    if not router_token:
        _print(f"  {err('[ERR]')} ROUTER_AUTH_TOKEN kosong")
        return False

    try:
        resp = std_requests.get(
            f"{router_base}/api/oauth/grok-cli/device-code",
            cookies={"auth_token": router_token},
            headers={"Accept": "*/*"},
            timeout=15,
        )
        if resp.status_code != 200:
            _print(f"  {err('[ERR]')} 9router HTTP {resp.status_code}")
            return False
        data = resp.json()
    except Exception as e:
        _print(f"  {err('[ERR]')} 9router unreachable: {e}")
        return False

    device_code = data.get("device_code") or data.get("deviceCode")
    code_verifier = data.get("codeVerifier") or data.get("code_verifier")
    user_code = data.get("user_code") or data.get("userCode")
    if not device_code or not user_code:
        _print(f"  {err('[ERR]')} device_code/user_code missing")
        return False

    session = make_session(proxy)
    session.cookies.update(cookies)
    auth_headers = {
        "content-type": "application/x-www-form-urlencoded",
        "origin": "https://accounts.x.ai",
        "referer": f"https://accounts.x.ai/oauth2/device?user_code={user_code}",
    }

    try:
        session.post(
            "https://auth.x.ai/oauth2/device/verify",
            data=f"user_code={user_code}",
            headers=auth_headers,
            timeout=20,
            allow_redirects=True,
        )
    except Exception as e:
        _print(f"  {err('[ERR]')} verify: {e}")
        return False

    auth_headers["referer"] = f"https://accounts.x.ai/oauth2/device/consent?user_code={user_code}"
    try:
        session.post(
            "https://auth.x.ai/oauth2/device/approve",
            data=f"user_code={user_code}&action=allow&principal_type=User&principal_id=",
            headers=auth_headers,
            timeout=20,
            allow_redirects=True,
        )
    except Exception as e:
        _print(f"  {err('[ERR]')} approve: {e}")
        return False

    # poll with retry — grok-cli callback kadang access denied
    for attempt in range(1, poll_retries + 1):
        try:
            poll = std_requests.post(
                f"{router_base}/api/oauth/grok-cli/poll",
                json={
                    "deviceCode": device_code,
                    "codeVerifier": code_verifier,
                    "extraData": None,
                },
                cookies={"auth_token": router_token},
                headers={"Accept": "*/*", "Content-Type": "application/json"},
                timeout=15,
            )
            if poll.status_code == 200:
                body = poll.json() if poll.text else {}
                if body.get("success") is True:
                    _print(f"  {ok('[OK]')} 9router connected")
                    return True
                # pending → tunggu
                if body.get("pending"):
                    time.sleep(2)
                    continue
                err_msg = body.get("error") or body.get("errorDescription") or poll.text[:120]
                if attempt < poll_retries:
                    time.sleep(2)
                    continue
                _print(f"  {err('[ERR]')} poll: {err_msg}")
                return False
        except Exception as e:
            if attempt < poll_retries:
                time.sleep(2)
                continue
            _print(f"  {err('[ERR]')} poll: {e}")
            return False
    return False


# ── Browser signup (Camoufox headless only) ──────────────────────────
def register_one(
    password: str,
    proxy: str | None,
    router: bool,
    router_base: str,
    router_token: str,
    worker_id: int = 0,
) -> bool:
    prefix = f"{dim(f'[#{worker_id}]')}" if worker_id else ""
    email = random_email()
    given = random.choice(FIRST_NAMES)
    family = random.choice(LAST_NAMES)
    _print(f"\n{prefix} {step('➤')} {bold(email)} — {given} {family}")

    mail = TempEmail(email)
    mail.warm()

    from camoufox.sync_api import Camoufox

    launch: dict = {"headless": True}
    if proxy:
        from urllib.parse import urlparse

        p = urlparse(proxy)
        pcfg: dict = {"server": f"{p.scheme}://{p.hostname}:{p.port}"}
        if p.username:
            pcfg["username"] = p.username
        if p.password:
            pcfg["password"] = p.password
        launch["proxy"] = pcfg
        launch["geoip"] = True

    uid = "-"
    cookies: dict = {}
    try:
        with Camoufox(**launch) as browser:
            page = browser.new_page()

            # 1) signup page
            _print(f"{prefix}  {step('[1/5]')} {warn('signup...')}")
            page.goto("https://accounts.x.ai/sign-up", wait_until="domcontentloaded", timeout=30_000)
            time.sleep(1.5)

            try:
                btn = page.locator("#onetrust-accept-btn-handler")
                if btn.count() > 0:
                    btn.click(timeout=2_000, force=True)
                    time.sleep(0.3)
            except Exception:
                pass

            page.click("text=Sign up with email", timeout=10_000)
            time.sleep(1)

            # 2) email
            page.fill('input[type="email"]', email)
            time.sleep(0.3)
            page.click('button[type="submit"]', timeout=8_000)
            time.sleep(2)
            _print(f"{prefix}  {step('[2/5]')} {ok('email sent')}")

            # 3) OTP
            code = mail.wait_code(retries=20, delay=3)
            if not code:
                _print(f"{prefix}  {err('[ERR]')} OTP timeout")
                return False
            _print(f"{prefix}  {step('[3/5]')} {ok('OTP')} {bold(code)}")

            otp = page.locator('input[name="code"]')
            if otp.count() == 0:
                _print(f"{prefix}  {err('[ERR]')} no OTP input")
                return False
            otp.fill(code)
            time.sleep(0.3)
            page.click('button[type="submit"]', timeout=5_000)
            time.sleep(2.5)

            # 4) password
            pwd = page.locator('input[type="password"]')
            if pwd.count() > 0:
                pwd.first.fill(password)
                time.sleep(0.2)
                if pwd.count() > 1:
                    pwd.nth(1).fill(password)
                page.click('button[type="submit"]', timeout=5_000)
                time.sleep(2.5)

            # 5) name
            fn = page.locator('input[name="firstName"], input[autocomplete="given-name"]')
            ln = page.locator('input[name="lastName"], input[autocomplete="family-name"]')
            if fn.count() > 0:
                fn.fill(given)
                ln.fill(family)
                time.sleep(0.2)
                page.click('button[type="submit"]', timeout=5_000)
                time.sleep(3)

            # 6) tunggu SSO — cookie sso sering baru set setelah redirect console
            def _all() -> dict:
                return {c["name"]: c["value"] for c in page.context.cookies()}

            cookies = _all()
            for i in range(1, 9):
                if "sso" in cookies or "sso-rw" in cookies:
                    break
                try:
                    if i in (1, 3, 5):
                        page.goto(
                            "https://console.x.ai/home",
                            wait_until="domcontentloaded",
                            timeout=20_000,
                        )
                    elif i in (2, 4):
                        page.goto(
                            "https://accounts.x.ai/account",
                            wait_until="domcontentloaded",
                            timeout=20_000,
                        )
                    else:
                        page.reload(wait_until="domcontentloaded", timeout=15_000)
                except Exception:
                    pass
                time.sleep(2)
                cookies = _all()

            # Signup form lolos = akun OK; sso optional (kadang delay / HttpOnly domain)
            if "sso" not in cookies and "sso-rw" not in cookies:
                if "cf_clearance" not in cookies and not cookies:
                    _print(f"{prefix}  {err('[ERR]')} no session cookies")
                    return False
                _print(f"{prefix}  {warn('[!]')} sso belum terlihat, lanjut 9router")
            else:
                _print(f"{prefix}  {ok('[OK]')} akun OK")

            uid = extract_uid(cookies)
            _print(f"{prefix}  {step('[4/5]')} uid={dim(str(uid)[:36])}")

    except Exception as e:
        _print(f"{prefix}  {err('[ERR]')} browser: {e}")
        return False

    router_status = "-"
    if router and cookies:
        ok_r = connect_to_router(
            cookies=cookies,
            router_base=router_base,
            router_token=router_token,
            proxy=proxy,
            poll_retries=5,
        )
        router_status = "connected" if ok_r else "failed"

    ts = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{email}|{password}|{given} {family}|{uid}|router={router_status}|{ts}\n"
    with _print_lock:
        with open("accounts.txt", "a", encoding="utf-8") as f:
            f.write(line)
    _print(f"{prefix}  {step('[5/5]')} {ok('saved')} → accounts.txt")
    return True


# ── Main ─────────────────────────────────────────────────────────────
def main() -> int:
    try:
        count = int(input(f"{info('?')} Berapa akun? "))
    except (ValueError, EOFError):
        count = 1
    try:
        threads = int(input(f"{info('?')} Thread? [1] "))
    except (ValueError, EOFError):
        threads = 1
    proxy = None
    try:
        if input(f"{info('?')} Proxy? (y/n) ").strip().lower() == "y":
            proxy = input(f"{info('?')} Proxy URL: ").strip() or None
    except EOFError:
        pass

    count = max(1, count)
    threads = max(1, min(threads, count))
    password = DEFAULT_PASSWORD
    router = bool(ROUTER_AUTH_TOKEN)

    _print(f"\n {step('➤')} {bold(str(count))} akun · {bold(str(threads))} thread · headless")
    if not router:
        _print(f" {warn('[!]')} ROUTER_AUTH_TOKEN kosong — skip 9router")
    _print(dim("=" * 46))

    results = {"ok": 0, "fail": 0}
    lock = _threading.Lock()
    t0 = _dt.datetime.now()

    def worker(wid: int):
        ok_r = register_one(
            password=password,
            proxy=proxy,
            router=router,
            router_base=ROUTER_BASE,
            router_token=ROUTER_AUTH_TOKEN,
            worker_id=wid,
        )
        with lock:
            results["ok" if ok_r else "fail"] += 1

    pending = list(range(1, count + 1))
    while pending:
        batch = pending[:threads]
        pending = pending[threads:]
        ts = [_threading.Thread(target=worker, args=(w,), daemon=True) for w in batch]
        for t in ts:
            t.start()
        for t in ts:
            t.join()

    elapsed = int((_dt.datetime.now() - t0).total_seconds())
    m, s = divmod(elapsed, 60)
    _print(f"\n{dim('=' * 46)}")
    _print(f" {ok('[OK]')} Berhasil : {ok(str(results['ok']))}")
    if results["fail"]:
        _print(f" {err('[ERR]')} Gagal    : {err(str(results['fail']))}")
    _print(f" {info('[i]')} Waktu    : {bold(f'{m}m {s}s')}")
    _print(f" {step('➤')} accounts.txt")
    return 0 if results["fail"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
