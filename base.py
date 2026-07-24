"""xAI console signup via API:
DARI AI UNTUK AI
"""

from __future__ import annotations

import argparse
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

BASE = "https://console.x.ai"
SEND_URL = f"{BASE}/api/auth/send-verification-code"
VERIFY_URL = f"{BASE}/api/auth/sign-up/verify-email"
CREATE_URL = f"{BASE}/api/auth/sign-up/create-account"

EMAIL_DOMAIN = "hungtpt.site"
GENERATOR_BASE = "https://generator.email"
DEFAULT_PASSWORD = os.getenv("DEFAULT_PASSWORD", "LauSapeEmpruy88@@")

TURNSTILE_SITEKEY = "0x4AAAAAAAhr9JGVDZbrZOo0"
TURNSTILE_PAGE_URL = f"{BASE}/login?mode=sign-up"
TURNSTILE_SOLVER_BASE = os.getenv("TURNSTILE_SOLVER_BASE", "")  # local solver URL
CAPSOLVER_API_KEY = os.getenv("CAPSOLVER_API_KEY", "")
TWOCAPTCHA_API_KEY = os.getenv("TWOCAPTCHA_API_KEY", "")

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
    "James", "Oliver", "Liam", "Noah", "Ethan", "Mason", "Logan", "Lucas",
    "Aiden", "Jackson", "Sebastian", "Mateo", "Jack", "Owen", "Theodore",
    "Emma", "Olivia", "Ava", "Sophia", "Isabella", "Mia", "Charlotte",
    "Amelia", "Harper", "Evelyn", "Abigail", "Emily", "Luna", "Sofia", "Ella",
    "Ahmad", "Rafi", "Dimas", "Budi", "Andi", "Sari", "Putri", "Dewi",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Wilson", "Moore", "Taylor", "Anderson", "Thomas", "Jackson",
    "White", "Harris", "Martin", "Thompson", "Robinson", "Clark", "Lewis",
    "Young", "Walker", "Hall", "Allen", "King", "Wright", "Scott", "Green",
    "Udin", "Pratama", "Saputra", "Wijaya", "Nugraha", "Santoso",
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
                print(f"  ... inbox error ({attempt}/{max_retries}): {e}")
                code = None
            if code:
                print()  # finish the waiting line cleanly
                return code
            if attempt < max_retries:
                print(f"  ... waiting OTP ({attempt}/{max_retries})   ", end="\r", flush=True)
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


def _valid_token(token: object) -> str | None:
    if isinstance(token, str) and len(token) > 40 and " " not in token.strip():
        return token.strip().strip('"')
    return None


def solve_turnstile_capsolver(
    sitekey: str = TURNSTILE_SITEKEY,
    page_url: str = TURNSTILE_PAGE_URL,
    api_key: str = CAPSOLVER_API_KEY,
    max_wait: int = 120,
    proxy: str | None = None,
) -> str:
    """Pure HTTP: CapSolver AntiTurnstileTask."""
    if not api_key:
        raise RuntimeError("CAPSOLVER_API_KEY empty")

    task: dict = {
        "type": "AntiTurnstileTaskProxyLess",
        "websiteURL": page_url,
        "websiteKey": sitekey,
    }
    if proxy:
        # http://user:pass@host:port -> CapSolver proxy format
        from urllib.parse import urlparse

        p = urlparse(proxy)
        task = {
            "type": "AntiTurnstileTask",
            "websiteURL": page_url,
            "websiteKey": sitekey,
            "proxyType": (p.scheme or "http").replace("socks5h", "socks5"),
            "proxyAddress": p.hostname,
            "proxyPort": p.port,
        }
        if p.username:
            task["proxyLogin"] = p.username
        if p.password:
            task["proxyPassword"] = p.password

    create = std_requests.post(
        "https://api.capsolver.com/createTask",
        json={"clientKey": api_key, "task": task},
        timeout=30,
    )
    create.raise_for_status()
    cdata = create.json()
    if cdata.get("errorId"):
        raise RuntimeError(f"capsolver create: {cdata.get('errorDescription') or cdata}")
    task_id = cdata.get("taskId")
    if not task_id:
        raise RuntimeError(f"capsolver no taskId: {cdata}")

    deadline = time.time() + max_wait
    while time.time() < deadline:
        time.sleep(2)
        poll = std_requests.post(
            "https://api.capsolver.com/getTaskResult",
            json={"clientKey": api_key, "taskId": task_id},
            timeout=30,
        )
        poll.raise_for_status()
        pdata = poll.json()
        if pdata.get("errorId"):
            raise RuntimeError(f"capsolver result: {pdata.get('errorDescription') or pdata}")
        status = str(pdata.get("status", "")).lower()
        if status == "ready":
            sol = pdata.get("solution") or {}
            token = _valid_token(sol.get("token") or sol.get("gRecaptchaResponse"))
            if token:
                return token
            raise RuntimeError(f"capsolver empty token: {pdata}")
        if status in {"failed", "error"}:
            raise RuntimeError(f"capsolver failed: {pdata}")
    raise RuntimeError("capsolver timeout")


def solve_turnstile_2captcha(
    sitekey: str = TURNSTILE_SITEKEY,
    page_url: str = TURNSTILE_PAGE_URL,
    api_key: str = TWOCAPTCHA_API_KEY,
    max_wait: int = 120,
    proxy: str | None = None,
) -> str:
    """Pure HTTP: 2Captcha turnstile."""
    if not api_key:
        raise RuntimeError("TWOCAPTCHA_API_KEY empty")

    params = {
        "key": api_key,
        "method": "turnstile",
        "sitekey": sitekey,
        "pageurl": page_url,
        "json": 1,
    }
    if proxy:
        from urllib.parse import urlparse

        p = urlparse(proxy)
        params["proxy"] = (
            f"{p.username}:{p.password}@{p.hostname}:{p.port}"
            if p.username
            else f"{p.hostname}:{p.port}"
        )
        params["proxytype"] = (p.scheme or "HTTP").upper().replace("SOCKS5H", "SOCKS5")

    create = std_requests.get("https://2captcha.com/in.php", params=params, timeout=30)
    create.raise_for_status()
    cdata = create.json()
    if cdata.get("status") != 1:
        raise RuntimeError(f"2captcha create: {cdata.get('request') or cdata}")
    req_id = cdata["request"]

    deadline = time.time() + max_wait
    while time.time() < deadline:
        time.sleep(5)
        poll = std_requests.get(
            "https://2captcha.com/res.php",
            params={"key": api_key, "action": "get", "id": req_id, "json": 1},
            timeout=30,
        )
        poll.raise_for_status()
        pdata = poll.json()
        if pdata.get("status") == 1:
            token = _valid_token(pdata.get("request"))
            if token:
                return token
            raise RuntimeError(f"2captcha empty token: {pdata}")
        if pdata.get("request") != "CAPCHA_NOT_READY":
            raise RuntimeError(f"2captcha result: {pdata.get('request') or pdata}")
    raise RuntimeError("2captcha timeout")


def solve_turnstile_local(
    sitekey: str = TURNSTILE_SITEKEY,
    page_url: str = TURNSTILE_PAGE_URL,
    solver_base: str = TURNSTILE_SOLVER_BASE,
    max_wait: int = 180,
    poll_every: float = 2.0,
) -> str:
    """Pure HTTP: local turnstile solver service."""
    if not solver_base:
        raise RuntimeError("TURNSTILE_SOLVER_BASE empty")

    create_url = (
        f"{solver_base.rstrip('/')}/turnstile"
        f"?url={quote(page_url, safe='')}"
        f"&sitekey={quote(sitekey, safe='')}"
    )
    create_resp = std_requests.get(create_url, timeout=15)
    create_resp.raise_for_status()
    create_data = create_resp.json()
    task_id = create_data.get("task_id") or create_data.get("id")
    if not task_id:
        raise RuntimeError(f"local solver no task_id: {create_data}")

    result_url = f"{solver_base.rstrip('/')}/result?id={quote(str(task_id), safe='')}"
    deadline = time.time() + max_wait
    while time.time() < deadline:
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

        ok = _valid_token(token)
        if ok:
            return ok
        if status in {"failed", "error", "fail"}:
            raise RuntimeError(f"local solver failed: {data or text[:200]}")
        time.sleep(poll_every)
    raise RuntimeError("local solver timeout")


def solve_turnstile_camoufox(
    sitekey: str = TURNSTILE_SITEKEY,
    page_url: str = TURNSTILE_PAGE_URL,
    proxy: str | None = None,
    timeout_ms: int = 120_000,
) -> str:
    """Gratis, no API key. No page.evaluate (CSP). init_script + console + CDP input + click widget."""
    from camoufox.sync_api import Camoufox

    # virtual display = Linux only; macOS/Windows pakai headless=True biasa
    # TURNSTILE_HEADED=1 buka window browser (debug)
    headed = os.getenv("TURNSTILE_HEADED", "").strip().lower() in {"1", "true", "yes", "y"}
    if headed:
        headless_mode: bool | str = False
    elif sys.platform.startswith("linux"):
        headless_mode = "virtual"
    else:
        headless_mode = True

    launch_kw: dict = {"headless": headless_mode, "humanize": True}
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

    held: dict = {"token": None}

    def take(tok: object) -> None:
        ok = _valid_token(tok)
        if ok:
            held["token"] = ok

    def on_console(msg) -> None:
        try:
            text = msg.text
        except Exception:
            return
        if "TURNSTILE_TOKEN:" in text:
            take(text.split("TURNSTILE_TOKEN:", 1)[1].strip())

    def on_response(resp) -> None:
        try:
            url = resp.url.lower()
            if "challenges.cloudflare.com" not in url and "turnstile" not in url:
                return
            ctype = (resp.headers or {}).get("content-type", "")
            if "json" not in ctype and "text" not in ctype:
                return
            body = resp.text()
            if not body or len(body) < 40:
                return
            # token-like string in CF responses
            m = re.search(r"\b(0\.[a-zA-Z0-9_\-\.]{80,})\b", body)
            if m:
                take(m.group(1))
            m2 = re.search(r'"token"\s*:\s*"([^"]{40,})"', body)
            if m2:
                take(m2.group(1))
        except Exception:
            pass

    # runs before page scripts; CSP does not block init_script
    hook_js = f"""
    (() => {{
      const SK = {json.dumps(sitekey)};
      window.__ts_token = null;
      const emit = (t) => {{
        if (typeof t === 'string' && t.length > 40) {{
          window.__ts_token = t;
          console.log('TURNSTILE_TOKEN:' + t);
        }}
      }};
      window.addEventListener('message', (ev) => {{
        try {{
          let d = ev.data;
          if (typeof d === 'string') {{
            if (d.length > 40 && d.indexOf('.') > 0) emit(d);
            try {{ d = JSON.parse(d); }} catch (e) {{ return; }}
          }}
          if (!d || typeof d !== 'object') return;
          const t = d.token || d.response || d['cf-turnstile-response']
            || (d.data && (d.data.token || d.data.response));
          emit(t);
        }} catch (e) {{}}
      }});
      const patch = () => {{
        if (!window.turnstile || window.turnstile.__ts_patched) return false;
        window.turnstile.__ts_patched = true;
        const origRender = window.turnstile.render.bind(window.turnstile);
        window.turnstile.render = (el, opts) => {{
          opts = Object.assign({{}}, opts || {{}});
          const prev = opts.callback;
          opts.callback = (t) => {{ emit(t); if (typeof prev === 'function') prev(t); }};
          if (!opts.sitekey) opts.sitekey = SK;
          return origRender(el, opts);
        }};
        if (typeof window.turnstile.ready === 'function') {{
          window.turnstile.ready(() => {{
            try {{
              if (document.querySelector('[name="cf-turnstile-response"]')) return;
              const div = document.createElement('div');
              div.id = 'ts-auto-widget';
              document.documentElement.appendChild(div);
              window.turnstile.render(div, {{
                sitekey: SK,
                callback: emit,
                'error-callback': () => {{}},
                'expired-callback': () => {{}},
              }});
            }} catch (e) {{}}
          }});
        }}
        return true;
      }};
      const iv = setInterval(() => {{ if (patch()) clearInterval(iv); }}, 30);
      setTimeout(() => clearInterval(iv), 90000);
      const scan = () => {{
        const inp = document.querySelector('input[name="cf-turnstile-response"], textarea[name="cf-turnstile-response"]');
        if (inp && inp.value) emit(inp.value);
      }};
      setInterval(scan, 500);
      const mo = new MutationObserver(scan);
      const boot = () => {{
        if (document.documentElement) mo.observe(document.documentElement, {{ childList: true, subtree: true, attributes: true, characterData: true }});
        scan();
      }};
      if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
      else boot();
    }})();
    """

    def read_inputs(page) -> str | None:
        sels = (
            'input[name="cf-turnstile-response"]',
            'textarea[name="cf-turnstile-response"]',
            "input[name='cf-turnstile-response']",
        )
        targets = [page] + list(page.frames)
        for ctx in targets:
            for sel in sels:
                try:
                    loc = ctx.locator(sel)
                    n = loc.count()
                    for i in range(n):
                        el = loc.nth(i)
                        try:
                            val = el.input_value(timeout=200)
                        except Exception:
                            try:
                                val = el.get_attribute("value")
                            except Exception:
                                val = None
                        ok = _valid_token(val)
                        if ok:
                            return ok
                except Exception:
                    continue
        return None

    def try_click_widget(page) -> None:
        # checkbox mode: click turnstile iframe
        try:
            for frame in page.frames:
                fu = (frame.url or "").lower()
                if "challenges.cloudflare.com" not in fu and "turnstile" not in fu:
                    continue
                for sel in ("input[type=checkbox]", "body", "#content", ".ctp-checkbox-label"):
                    try:
                        loc = frame.locator(sel)
                        if loc.count() > 0:
                            loc.first.click(timeout=800, force=True)
                            return
                    except Exception:
                        continue
        except Exception:
            pass
        try:
            page.locator("iframe[src*='challenges.cloudflare.com'], iframe[src*='turnstile']").first.click(
                timeout=800, force=True
            )
        except Exception:
            pass

    with Camoufox(**launch_kw) as browser:
        page = browser.new_page()
        page.on("console", on_console)
        page.on("response", on_response)
        page.add_init_script(hook_js)
        page.goto(page_url, wait_until="domcontentloaded", timeout=60_000)
        try:
            page.wait_for_load_state("networkidle", timeout=20_000)
        except Exception:
            pass

        deadline = time.time() + (timeout_ms / 1000)
        clicked = False
        while time.time() < deadline:
            if held["token"]:
                return held["token"]

            got = read_inputs(page)
            if got:
                return got

            if not clicked or int(time.time()) % 8 == 0:
                try_click_widget(page)
                clicked = True

            # static HTML scrape
            try:
                html = page.content()
                for pat in (
                    r'name=["\']cf-turnstile-response["\'][^>]*value=["\']([^"\']{40,})["\']',
                    r'value=["\']([^"\']{40,})["\'][^>]*name=["\']cf-turnstile-response["\']',
                    r"\b(0\.[a-zA-Z0-9_\-\.]{80,})\b",
                ):
                    m = re.search(pat, html)
                    if m:
                        ok = _valid_token(m.group(1))
                        if ok:
                            return ok
            except Exception:
                pass

            time.sleep(0.6)

    raise RuntimeError(f"camoufox turnstile bad token: {held['token']!r}")


def solve_turnstile(
    sitekey: str = TURNSTILE_SITEKEY,
    page_url: str = TURNSTILE_PAGE_URL,
    solver_base: str = TURNSTILE_SOLVER_BASE,
    max_wait: int = 180,
    poll_every: float = 2.0,
    proxy: str | None = None,
) -> str:
    """Priority: CapSolver API → 2Captcha API → local solver URL → camoufox browser."""
    errors: list[str] = []

    # 1) CapSolver pure API
    key = CAPSOLVER_API_KEY
    if key:
        try:
            return solve_turnstile_capsolver(
                sitekey=sitekey, page_url=page_url, api_key=key, max_wait=max_wait, proxy=proxy
            )
        except Exception as e:
            errors.append(f"capsolver: {e}")

    # 2) 2Captcha pure API
    key2 = TWOCAPTCHA_API_KEY
    if key2:
        try:
            return solve_turnstile_2captcha(
                sitekey=sitekey, page_url=page_url, api_key=key2, max_wait=max_wait, proxy=proxy
            )
        except Exception as e:
            errors.append(f"2captcha: {e}")

    # 3) local HTTP solver
    base = solver_base or TURNSTILE_SOLVER_BASE
    if base:
        try:
            return solve_turnstile_local(
                sitekey=sitekey,
                page_url=page_url,
                solver_base=base,
                max_wait=max_wait,
                poll_every=poll_every,
            )
        except Exception as e:
            errors.append(f"local: {e}")

    # 4) browser fallback
    try:
        return solve_turnstile_camoufox(sitekey=sitekey, page_url=page_url, proxy=proxy)
    except Exception as e:
        errors.append(f"camoufox: {e}")

    raise RuntimeError("turnstile solve failed | " + " | ".join(errors))


def print_resp(label: str, resp: cffi_requests.Response, verbose: bool = False) -> None:
    body = resp.text
    ok = resp.status_code < 400
    icon = "âœ“" if ok else "âœ—"
    if "cloudflare" in body.lower() and len(body) > 400:
        tag = "BLOCKED" if "Sorry, you have been blocked" in body else "CF-HTML"
        print(f"  {icon} [{label}] {resp.status_code} {tag}")
        return
    if verbose or not ok:
        try:
            j = resp.json()
            print(f"  {icon} [{label}] {resp.status_code} {json.dumps(j)}")
        except Exception:
            print(f"  {icon} [{label}] {resp.status_code} {body[:300]}")
    else:
        print(f"  {icon} [{label}] {resp.status_code} ok")


def connect_to_router(
    session: cffi_requests.Session,
    router_base: str = ROUTER_BASE,
    router_token: str = ROUTER_AUTH_TOKEN,
    proxy: str | None = None,
) -> bool:
    """Authorize new xAI account to 9router ” pure API, no browser needed."""
    print("\n[+] Menghubungkan akun ke 9router...")
    try:
        resp = std_requests.get(
            f"{router_base}/api/oauth/grok-cli/device-code",
            cookies={"auth_token": router_token},
            headers={"Accept": "*/*"},
            timeout=15,
        )
        if resp.status_code != 200:
            print(f" ✘ 9router tidak merespons (kode {resp.status_code})")
            return False
        data = resp.json()
    except Exception as e:
        print(f"  ✘ 9router tidak dapat dijangkau: {e}")
        return False

    verify_url = data.get("verification_uri_complete") or data.get("verificationUriComplete")
    device_code = data.get("device_code") or data.get("deviceCode")
    code_verifier = data.get("codeVerifier") or data.get("code_verifier")
    user_code = data.get("user_code") or data.get("userCode")
    auth_headers = {
        "content-type": "application/x-www-form-urlencoded",
        "origin": "https://accounts.x.ai",
        "referer": f"https://accounts.x.ai/oauth2/device?user_code={user_code}",
    }

    # Step 1: verify (Continue button)
    try:
        r1 = session.post(
            "https://auth.x.ai/oauth2/device/verify",
            data=f"user_code={user_code}",
            headers=auth_headers,
            timeout=20,
            allow_redirects=True,
        )
    except Exception as e:
        print(f"  ✘ Gagal menghubungkan (langkah 1): {e}")
        return False

    # Step 2: approve (Allow button)
    auth_headers["referer"] = f"https://accounts.x.ai/oauth2/device/consent?user_code={user_code}"
    try:
        r2 = session.post(
            "https://auth.x.ai/oauth2/device/approve",
            data=f"user_code={user_code}&action=allow&principal_type=User&principal_id=",
            headers=auth_headers,
            timeout=20,
            allow_redirects=True,
        )
    except Exception as e:
        print(f"  ✘ Gagal menghubungkan (langkah 2): {e}")
        return False

    # Step 3: poll 9router
    poll_resp = std_requests.post(
        f"{router_base}/api/oauth/grok-cli/poll",
        json={"deviceCode": device_code, "codeVerifier": code_verifier, "extraData": None},
        cookies={"auth_token": router_token},
        headers={"Accept": "*/*", "Content-Type": "application/json"},
        timeout=15,
    )
    if poll_resp.status_code == 200:
        print("  ✔ Akun berhasil terhubung ke 9router!")
        return True
    else:
        print(f"  ✘ Koneksi 9router gagal: {poll_resp.text[:200]}")
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
    """Buat satu akun. Return True jika berhasil."""
    prefix = f"[#{worker_id}] " if worker_id else ""

    email = random_email()
    given_name = random.choice(FIRST_NAMES)
    family_name = random.choice(LAST_NAMES)

    _safe_print(f"\n{prefix} ➤ {email}  - {given_name} {family_name}")

    # inbox
    mail = TempEmail(email, proxy=None)
    try:
        mail.warm()
    except Exception:
        pass

    # session
    session = make_session(args.impersonate, args.proxy)
    if not args.no_warmup:
        try:
            warmup(session)
        except Exception:
            pass

    # 1) send code
    try:
        send_resp = send_code(session, email)
    except Exception as e:
        _safe_print(f"{prefix}  ✘ Gagal mengirim kode: {e}")
        return False
    if send_resp.status_code >= 400:
        try:
            err = send_resp.json().get("error") or send_resp.text[:80]
        except Exception:
            err = send_resp.text[:80]
        _safe_print(f"{prefix}  ✘ Email ditolak: {err}")
        return False
    _safe_print(f"{prefix}  [1/4] Kode verifikasi terkirim!")

    # 2) OTP
    code = mail.wait_for_code(max_retries=args.otp_retries, delay=args.otp_delay)
    if not code:
        _safe_print(f"{prefix}  ✘ Kode OTP tidak diterima")
        return False
    _safe_print(f"{prefix}  [2/4] Kode OTP diterima: {code}")

    # 3) verify email
    try:
        verify_resp = verify_email(session, email, code)
    except Exception as e:
        _safe_print(f"{prefix}  ✘ Gagal verifikasi: {e}")
        return False
    if verify_resp.status_code >= 400:
        _safe_print(f"{prefix}  ✘ Kode tidak valid")
        return False
    _safe_print(f"{prefix}  [3/4] Email terverifikasi, melewati keamanan...")

    # 4) turnstile
    try:
        token = solve_turnstile(
            sitekey=args.sitekey,
            page_url=TURNSTILE_PAGE_URL,
            solver_base=args.solver,
            max_wait=args.turnstile_wait,
            proxy=args.proxy,
        )
    except Exception as e:
        _safe_print(f"{prefix}  ✘ Verifikasi keamanan gagal: {e}")
        return False

    # 5) create account
    try:
        create_resp = create_account(
            session=session,
            email=email,
            password=args.password,
            given_name=given_name,
            family_name=family_name,
            email_code=code,
            turnstile_token=token,
        )
    except Exception as e:
        _safe_print(f"{prefix}  ✘ Gagal membuat akun: {e}")
        return False

    if create_resp.status_code >= 400:
        try:
            err = create_resp.json().get("error") or create_resp.text[:80]
        except Exception:
            err = create_resp.text[:80]
        _safe_print(f"{prefix}  ✗ Gagal membuat akun: {err}")
        return False

    try:
        uid = create_resp.json().get("session", {}).get("userId", "-")
    except Exception:
        uid = "-"
    _safe_print(f"{prefix}  [4/4]  ✔ Akun berhasil dibuat!")

    # 6) 9router
    router_status = "-"
    if args.router:
        ok = connect_to_router(
            session=session,
            router_base=args.router_base,
            router_token=args.router_token,
            proxy=args.proxy,
        )
        router_status = "connected" if ok else "failed"

    # simpan ke accounts.txt
    ts = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{email}|{args.password}|{given_name} {family_name}|{uid}|router={router_status}|{ts}\n"
    with _print_lock_fn():
        with open("accounts.txt", "a", encoding="utf-8") as f:
            f.write(line)
    _safe_print(f"{prefix}  ✔ Tersimpan ➤ accounts.txt")
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
            args.count = int(input("Berapa banyak akun yang ingin dibuat? "))
        except (ValueError, EOFError):
            args.count = 1
    if args.threads is None:
        try:
            args.threads = int(input("Berapa thread (proses paralel)? [1 = satu-satu] "))
        except (ValueError, EOFError):
            args.threads = 1
    if args.proxy is None:
        try:
            pakai = input("Mau pakai proxy? (y/n) ").strip().lower()
            if pakai == "y":
                args.proxy = input("Masukkan proxy (http://user:pass@host:port): ").strip() or None
        except EOFError:
            pass

    args.count = max(1, args.count)
    args.threads = max(1, min(args.threads, args.count))

    print(f"\n ➤ Membuat {args.count} akun dengan {args.threads} thread...")
    print("=" * 46)

    results = {"ok": 0, "fail": 0}
    lock = _threading.Lock()
    start_time = _dt.datetime.now()

    def worker(wid: int):
        ok = register_one(args, worker_id=wid)
        with lock:
            if ok:
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

    print("\n" + "=" * 46)
    print(f" ✔ Berhasil : {results['ok']}")
    if results["fail"]:
        print(f" ✗ Gagal    : {results['fail']}")
    print(f" ⏲ Waktu    : {menit} menit {detik} detik")
    print(f" ➤ Lihat akun di: accounts.txt")
    return 0 if results["fail"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())