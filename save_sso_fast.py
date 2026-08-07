"""save_sso_fast.py — Full Camoufox signup + SSO cookies → JSON.
Flow sama persis ternakgrok.py / save_sso_cookies.py (proven).
Log step-by-step detail. No 9router. No CapSolver.
"""
from __future__ import annotations

import base64
import datetime as _dt
import json
import os
import random
import re
import string
import threading as _threading
import time
from urllib.parse import urlparse

from dotenv import load_dotenv
import requests as std_requests

load_dotenv()


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


_print_lock = _threading.Lock()
_json_lock = _threading.Lock()


def _print(*a, **kw):
    with _print_lock:
        print(*a, **kw)


DEFAULT_PASSWORD = os.getenv("DEFAULT_PASSWORD", "LauSapeEmpruy88@@")
EMAIL_DOMAINS = [
    d.strip()
    for d in os.getenv("EMAIL_DOMAINS", "hungtpt.site").split(",")
    if d.strip()
]
GENERATOR_BASE = "https://generator.email"
JSON_FILE = "accounts_cookies.json"

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


def random_email(length: int = 8) -> str:
    chars = string.ascii_lowercase + string.digits
    user = "".join(random.choices(chars, k=length))
    return f"{user}@{random.choice(EMAIL_DOMAINS)}"


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

    def wait_code(self, prefix: str = "", retries: int = 25, delay: float = 3) -> str | None:
        for i in range(1, retries + 1):
            code = self.extract(self._inbox())
            if code:
                _print()
                return code
            if i < retries:
                with _print_lock:
                    print(
                        f"{prefix}  {warn('...')} tunggu OTP inbox ({i}/{retries})   ",
                        end="\r",
                        flush=True,
                    )
                time.sleep(delay)
        _print()
        return None


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


def save_account_json(account: dict) -> None:
    with _json_lock:
        existing: list = []
        if os.path.exists(JSON_FILE) and os.path.getsize(JSON_FILE) > 0:
            try:
                with open(JSON_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    existing = data
                elif isinstance(data, dict):
                    existing = [data]
            except Exception:
                existing = []
        existing.append(account)
        with open(JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)


def _proxy_launch(proxy: str | None) -> dict:
    launch: dict = {"headless": True}
    if proxy:
        p = urlparse(proxy)
        pcfg: dict = {"server": f"{p.scheme}://{p.hostname}:{p.port}"}
        if p.username:
            pcfg["username"] = p.username
        if p.password:
            pcfg["password"] = p.password
        launch["proxy"] = pcfg
        launch["geoip"] = True
    return launch


def _wait_locator(page, selector: str, prefix: str, label: str, retries: int = 15, delay: float = 1.0):
    """Tunggu element muncul. Return locator atau None."""
    for i in range(1, retries + 1):
        loc = page.locator(selector)
        try:
            if loc.count() > 0:
                return loc
        except Exception:
            pass
        _print(f"{prefix}  {warn('...')} tunggu {label} ({i}/{retries})")
        time.sleep(delay)
    return None


def _page_debug(page, prefix: str) -> None:
    """Log URL + title + short snippet untuk debug form stuck."""
    try:
        url = page.url
    except Exception:
        url = "?"
    try:
        title = page.title()
    except Exception:
        title = "?"
    _print(f"{prefix}  {info('[i]')} page url={dim(url)}")
    _print(f"{prefix}  {info('[i]')} page title={dim(title)}")
    try:
        # cek error text di page
        body = page.locator("body").inner_text(timeout=2_000)[:300]
        body = re.sub(r"\s+", " ", body).strip()
        if body:
            _print(f"{prefix}  {info('[i]')} page text: {dim(body[:200])}")
    except Exception:
        pass


def register_one(
    password: str,
    proxy: str | None = None,
    worker_id: int = 0,
) -> tuple[bool, dict]:
    prefix = f"{dim(f'[#{worker_id}]')}" if worker_id else ""
    email = random_email()
    given = random.choice(FIRST_NAMES)
    family = random.choice(LAST_NAMES)
    _print(f"\n{prefix} {step('➤')} {bold(email)} — {given} {family}")

    _print(f"{prefix}  {step('[1/8]')} {warn('warm temp email inbox...')}")
    mail = TempEmail(email)
    mail.warm()
    _print(
        f"{prefix}  {ok('[OK]')} inbox ready → "
        f"{GENERATOR_BASE}/{mail.domain}/{mail.username}"
    )

    from camoufox.sync_api import Camoufox

    launch = _proxy_launch(proxy)
    uid = "-"
    cookies: dict = {}

    try:
        with Camoufox(**launch) as browser:
            page = browser.new_page()

            # ── 2) signup page ───────────────────────────────────────
            _print(f"{prefix}  {step('[2/8]')} {warn('buka accounts.x.ai/sign-up...')}")
            page.goto(
                "https://accounts.x.ai/sign-up",
                wait_until="domcontentloaded",
                timeout=30_000,
            )
            time.sleep(1.5)
            _print(f"{prefix}  {ok('[OK]')} signup page loaded")

            try:
                btn = page.locator("#onetrust-accept-btn-handler")
                if btn.count() > 0:
                    btn.click(timeout=2_000, force=True)
                    time.sleep(0.3)
                    _print(f"{prefix}  {info('[i]')} cookie consent accepted")
            except Exception:
                pass

            # ── 3) email ─────────────────────────────────────────────
            _print(f"{prefix}  {step('[3/8]')} {warn('Sign up with email + isi email...')}")
            page.click("text=Sign up with email", timeout=10_000)
            time.sleep(1)

            email_inp = _wait_locator(
                page, 'input[type="email"]', prefix, "email input", retries=10
            )
            if email_inp is None:
                _page_debug(page, prefix)
                _print(f"{prefix}  {err('[ERR]')} email input tidak muncul")
                return False, {}

            email_inp.fill(email)
            time.sleep(0.3)
            page.click('button[type="submit"]', timeout=8_000)
            time.sleep(2)
            _print(f"{prefix}  {ok('[OK]')} email submitted → OTP dikirim xAI")

            # ── 4) OTP ───────────────────────────────────────────────
            _print(f"{prefix}  {step('[4/8]')} {warn('tunggu OTP dari generator.email...')}")
            code = mail.wait_code(prefix=prefix, retries=25, delay=3)
            if not code:
                _print(f"{prefix}  {err('[ERR]')} OTP timeout")
                return False, {}
            _print(f"{prefix}  {ok('[OK]')} OTP diterima: {bold(code)}")

            _print(f"{prefix}  {step('[5/8]')} {warn(f'isi OTP {code} di form...')}")
            otp = _wait_locator(
                page, 'input[name="code"]', prefix, "OTP input", retries=15, delay=1
            )
            if otp is None:
                _page_debug(page, prefix)
                _print(f"{prefix}  {err('[ERR]')} OTP input tidak muncul")
                return False, {}

            otp.fill(code)
            time.sleep(0.3)
            page.click('button[type="submit"]', timeout=5_000)
            time.sleep(2.5)
            _print(f"{prefix}  {ok('[OK]')} OTP submitted")

            # ── 6) password (WAJIB) ───────────────────────────────────
            _print(f"{prefix}  {step('[6/8]')} {warn('isi password...')}")
            pwd = _wait_locator(
                page,
                'input[type="password"]',
                prefix,
                "password input",
                retries=20,
                delay=1,
            )
            if pwd is None:
                _page_debug(page, prefix)
                # cek apakah ada error OTP / turnstile
                _print(f"{prefix}  {err('[ERR]')} password input tidak muncul — form stuck")
                return False, {}

            pwd.first.fill(password)
            time.sleep(0.2)
            if pwd.count() > 1:
                pwd.nth(1).fill(password)
                _print(f"{prefix}  {info('[i]')} confirm password diisi")
            page.click('button[type="submit"]', timeout=5_000)
            time.sleep(2.5)
            _print(f"{prefix}  {ok('[OK]')} password submitted")

            # ── 7) name ──────────────────────────────────────────────
            _print(f"{prefix}  {step('[7/8]')} {warn('isi nama...')}")
            fn = _wait_locator(
                page,
                'input[name="firstName"], input[autocomplete="given-name"]',
                prefix,
                "firstName input",
                retries=15,
                delay=1,
            )
            ln = page.locator(
                'input[name="lastName"], input[autocomplete="family-name"]'
            )
            if fn is None:
                _page_debug(page, prefix)
                _print(f"{prefix}  {err('[ERR]')} name input tidak muncul")
                return False, {}

            fn.fill(given)
            ln.fill(family)
            time.sleep(0.2)
            page.click('button[type="submit"]', timeout=5_000)
            time.sleep(3)
            _print(f"{prefix}  {ok('[OK]')} name submitted: {given} {family}")

            # ── 8) collect SSO ───────────────────────────────────────
            _print(f"{prefix}  {step('[8/8]')} {warn('collect SSO cookies...')}")

            def _all() -> dict:
                return {c["name"]: c["value"] for c in page.context.cookies()}

            cookies = _all()
            for i in range(1, 11):
                if "sso" in cookies or "sso-rw" in cookies:
                    break
                try:
                    if i in (1, 3, 5, 7):
                        _print(f"{prefix}  {dim(f'  → console.x.ai/home ({i}/10)')}")
                        page.goto(
                            "https://console.x.ai/home",
                            wait_until="domcontentloaded",
                            timeout=20_000,
                        )
                    elif i in (2, 4, 6, 8):
                        _print(f"{prefix}  {dim(f'  → accounts.x.ai/account ({i}/10)')}")
                        page.goto(
                            "https://accounts.x.ai/account",
                            wait_until="domcontentloaded",
                            timeout=20_000,
                        )
                    else:
                        _print(f"{prefix}  {dim(f'  → reload ({i}/10)')}")
                        page.reload(wait_until="domcontentloaded", timeout=15_000)
                except Exception as e:
                    _print(f"{prefix}  {warn('[!]')} navigate: {e}")
                time.sleep(2)
                cookies = _all()

            keys = list(cookies.keys())
            # _print(f"{prefix}  {info('[i]')} cookie keys ({len(keys)}): {keys}")

            if "sso" not in cookies and "sso-rw" not in cookies:
                _page_debug(page, prefix)
                _print(f"{prefix}  {err('[ERR]')} SSO cookie tidak ada — akun gagal")
                return False, {}

            uid = extract_uid(cookies)
            _print(f"{prefix}  {ok('[OK]')} SSO didapat · uid={dim(str(uid)[:36])}")

    except Exception as e:
        _print(f"{prefix}  {err('[ERR]')} browser: {e}")
        return False, {}

    if not cookies or ("sso" not in cookies and "sso-rw" not in cookies):
        _print(f"{prefix}  {err('[ERR]')} final check: no SSO")
        return False, {}

    ts = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    account = {
        "email": email,
        "password": password,
        "name": f"{given} {family}",
        "uid": uid,
        "cookies": cookies,
        "timestamp": ts,
    }
    save_account_json(account)
    _print(
        f"{prefix}  {ok('[DONE]')} saved → {JSON_FILE} "
        f"(uid={dim(str(uid)[:36])} · cookies={len(cookies)} · sso=yes)"
    )
    return True, account


def main() -> int:
    try:
        count = int(input(f"{info('?')} Berapa akun? ").strip() or "1")
    except (ValueError, EOFError):
        count = 1
    try:
        threads = int(input(f"{info('?')} Thread? [1] ").strip() or "1")
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

    _print(f"\n {step('➤')} {bold(str(count))} akun · {bold(str(threads))} thread")
    _print(f" {info('[i]')} mode: full Camoufox signup (sama ternakgrok.py)")
    _print(f" {info('[i]')} domain: {', '.join(EMAIL_DOMAINS)}")
    _print(f" {info('[i]')} output: {JSON_FILE}")
    _print(f" {info('[i]')} simpan HANYA jika sso+uid ada")
    _print(dim("=" * 50))

    results = {"ok": 0, "fail": 0}
    lock = _threading.Lock()
    t0 = time.time()

    def worker(wid: int):
        ok_r, _ = register_one(password=password, proxy=proxy, worker_id=wid)
        with lock:
            results["ok" if ok_r else "fail"] += 1

    pending = list(range(1, count + 1))
    while pending:
        batch = pending[:threads]
        pending = pending[threads:]
        ts = [
            _threading.Thread(target=worker, args=(w,), daemon=True)
            for w in batch
        ]
        for t in ts:
            t.start()
        for t in ts:
            t.join()

    elapsed = int(time.time() - t0)
    m, s = divmod(elapsed, 60)
    _print(f"\n{dim('=' * 50)}")
    _print(f" {ok('[OK]')} Berhasil : {ok(str(results['ok']))}")
    if results["fail"]:
        _print(f" {err('[ERR]')} Gagal    : {err(str(results['fail']))}")
    _print(f" {info('[i]')} Waktu    : {bold(f'{m}m {s}s')}")
    _print(f" {step('➤')} {JSON_FILE}")
    return 0 if results["fail"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
