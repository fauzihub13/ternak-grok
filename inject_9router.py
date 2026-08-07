"""Inject akun ke 9router pakai SSO cookies dari accounts_cookies.json."""
from __future__ import annotations

import json
import os
import sys
import threading as _threading
import time

from curl_cffi import requests as cffi_requests
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


def _print(*a, **kw):
    with _print_lock:
        print(*a, **kw)


ROUTER_BASE = os.getenv("ROUTER_BASE", "http://localhost:20128")
ROUTER_AUTH_TOKEN = os.getenv("ROUTER_AUTH_TOKEN", "")
JSON_FILE = "accounts_cookies.json"
_json_lock = _threading.Lock()


def make_session(proxy: str | None = None) -> cffi_requests.Session:
    s = cffi_requests.Session(impersonate="chrome136")
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}
    return s


def load_accounts() -> list:
    if not os.path.exists(JSON_FILE) or os.path.getsize(JSON_FILE) == 0:
        return []
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    return []


def save_accounts(accounts: list) -> None:
    with _json_lock:
        with open(JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(accounts, f, ensure_ascii=False, indent=2)


def update_account_status(idx: int, status: str) -> None:
    with _json_lock:
        accounts = load_accounts()
        if 0 <= idx < len(accounts):
            accounts[idx]["router"] = status
            with open(JSON_FILE, "w", encoding="utf-8") as f:
                json.dump(accounts, f, ensure_ascii=False, indent=2)


def connect_to_router(
    cookies: dict,
    router_base: str = ROUTER_BASE,
    router_token: str = ROUTER_AUTH_TOKEN,
    proxy: str | None = None,
    poll_retries: int = 5,
) -> bool:
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
                    return True
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


def inject_one(
    idx: int,
    account: dict,
    proxy: str | None,
    worker_id: int = 0,
) -> bool:
    prefix = f"{dim(f'[#{worker_id}]')}" if worker_id else ""
    email = account.get("email") or "-"
    uid = account.get("uid") or "-"
    cookies = account.get("cookies") or {}
    _print(f"\n{prefix} {step('➤')} {bold(email)} uid={dim(str(uid)[:36])}")

    if not cookies:
        _print(f"{prefix}  {err('[ERR]')} cookies kosong")
        update_account_status(idx, "failed_no_cookies")
        return False
    if "sso" not in cookies and "sso-rw" not in cookies:
        _print(f"{prefix}  {warn('[!]')} no sso/sso-rw cookie")

    _print(f"{prefix}  {info('[+]')} Connect 9router...")
    ok_r = connect_to_router(
        cookies=cookies,
        router_base=ROUTER_BASE,
        router_token=ROUTER_AUTH_TOKEN,
        proxy=proxy,
        poll_retries=5,
    )
    if ok_r:
        update_account_status(idx, "connected")
        _print(f"{prefix}  {ok('[OK]')} 9router connected")
        return True
    update_account_status(idx, "failed")
    _print(f"{prefix}  {err('[ERR]')} 9router failed")
    return False


def main() -> int:
    if not ROUTER_AUTH_TOKEN:
        _print(f"{err('[ERR]')} ROUTER_AUTH_TOKEN kosong — set di .env")
        return 1

    accounts = load_accounts()
    if not accounts:
        _print(f"{err('[ERR]')} {JSON_FILE} kosong / tidak ada")
        return 1

    pending_idx = [
        i for i, a in enumerate(accounts)
        if a.get("router") != "connected" and a.get("cookies")
    ]
    total = len(accounts)
    already = total - len(pending_idx)
    _print(f" {info('[i]')} total={bold(str(total))} · pending={bold(str(len(pending_idx)))} · connected={bold(str(already))}")
    if not pending_idx:
        _print(f" {ok('[OK]')} semua akun sudah connected")
        return 0

    try:
        raw = input(f"{info('?')} Berapa akun inject? [all={len(pending_idx)}] ").strip()
        count = int(raw) if raw else len(pending_idx)
    except (ValueError, EOFError):
        count = len(pending_idx)
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

    count = max(1, min(count, len(pending_idx)))
    threads = max(1, min(threads, count))
    jobs = pending_idx[:count]

    _print(f"\n {step('➤')} inject {bold(str(count))} akun · {bold(str(threads))} thread")
    _print(f" {dim(f'9router={ROUTER_BASE}')}")
    _print(dim("=" * 46))

    results = {"ok": 0, "fail": 0}
    lock = _threading.Lock()
    t0 = time.time()

    def worker(job_n: int, acc_idx: int):
        # reload fresh account (status boleh berubah)
        accs = load_accounts()
        if acc_idx >= len(accs):
            with lock:
                results["fail"] += 1
            return
        ok_r = inject_one(
            idx=acc_idx,
            account=accs[acc_idx],
            proxy=proxy,
            worker_id=job_n,
        )
        with lock:
            results["ok" if ok_r else "fail"] += 1

    pending = list(enumerate(jobs, start=1))
    while pending:
        batch = pending[:threads]
        pending = pending[threads:]
        ts = [
            _threading.Thread(target=worker, args=(n, idx), daemon=True)
            for n, idx in batch
        ]
        for t in ts:
            t.start()
        for t in ts:
            t.join()

    elapsed = int(time.time() - t0)
    m, s = divmod(elapsed, 60)
    _print(f"\n{dim('=' * 46)}")
    _print(f" {ok('[OK]')} Berhasil : {ok(str(results['ok']))}")
    if results["fail"]:
        _print(f" {err('[ERR]')} Gagal    : {err(str(results['fail']))}")
    _print(f" {info('[i]')} Waktu    : {bold(f'{m}m {s}s')}")
    _print(f" {step('➤')} status diupdate di {JSON_FILE}")
    return 0 if results["fail"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
