"""
Aternos server auto-renewal script.

Keeps your Aternos server alive by periodically logging in and
interacting with the panel. Aternos deactivates servers after
~7 days of inactivity.

Usage:
    python3 renew.py

Environment variables:
    ATERNOS_USERNAME - Aternos username
    ATERNOS_PASSWORD - Aternos password
"""

import os
import sys
import hashlib
import random
import string
import json
import time
import logging
from curl_cffi import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

USERNAME = os.environ.get("ATERNOS_USERNAME", "")
PASSWORD = os.environ.get("ATERNOS_PASSWORD", "")
AJAX_TOKEN = "Kg5pUrtEcWixTBzGuE51"  # fallback
HCAPTCHA_SITEKEY = "ecf33f35-4807-4dcb-bd09-bcaf874e69cc"
CLOUDFLYER_URL = os.environ.get("CLOUDFLYER_URL", "http://localhost:3000")


def get_ajax_token(session) -> str:
    """Extract fresh AJAX token from the page."""
    import re
    try:
        resp = session.get(f"https://aternos.org/go")
        match = re.search(r'AJAX_TOKEN.*?["\']([A-Za-z0-9]{15,25})["\']', resp.text)
        if match:
            return match.group(1)
    except Exception:
        pass
    return AJAX_TOKEN


def random_string(length: int = 16) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


class AternosClient:
    BASE_URL = "https://aternos.org"

    def __init__(self):
        self.session = requests.Session(impersonate="chrome")
        self.logged_in = False

    def _ajax(self, endpoint: str, data: dict = None) -> dict:
        """Make an AJAX request to Aternos API."""
        key = random_string()
        value = random_string()
        path = f"/ajax/{endpoint}"
        self.session.cookies.set(
            f"ATERNOS_SEC_{key}", value,
            domain="aternos.org", path=path
        )
        url = f"{self.BASE_URL}{path}?TOKEN={AJAX_TOKEN}&SEC={key}:{value}"
        resp = self.session.post(
            url,
            data=data or {},
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Referer": f"{self.BASE_URL}/go",
                "Origin": self.BASE_URL,
            },
        )
        try:
            return resp.json()
        except Exception:
            # Response might be HTML (error page) or empty
            text = resp.text[:200]
            logger.error(f"Non-JSON response from {endpoint}: {text}")
            return {"success": False, "error": f"Non-JSON response: {text[:80]}"}

    def _solve_hcaptcha(self) -> str | None:
        """Solve hCaptcha using cloudflyer."""
        import requests as req
        try:
            resp = req.post(f"{CLOUDFLYER_URL}/createTask", json={
                "clientKey": "aternos",
                "type": "hcaptcha",
                "url": f"{self.BASE_URL}/go",
                "siteKey": HCAPTCHA_SITEKEY,
            }, timeout=15)
            data = resp.json()
            task_id = data.get("taskId")
            if not task_id:
                logger.error(f"hCaptcha task creation failed: {data}")
                return None

            logger.info(f"hCaptcha task created: {task_id}")
            for _ in range(60):
                time.sleep(3)
                resp = req.post(f"{CLOUDFLYER_URL}/getTaskResult", json={
                    "clientKey": "aternos",
                    "taskId": task_id,
                }, timeout=15)
                result = resp.json()
                if result.get("status") == "completed":
                    token = result.get("result", {}).get("response", {}).get("token") or result.get("result", {}).get("response")
                    if token:
                        logger.info(f"hCaptcha solved: {str(token)[:30]}...")
                        return token
                    return None
                elif result.get("status") == "failed":
                    logger.error(f"hCaptcha solve failed: {result}")
                    return None
            return None
        except Exception as e:
            logger.error(f"hCaptcha solve error: {e}")
            return None

    def login(self) -> bool:
        """Login to Aternos."""
        global AJAX_TOKEN
        AJAX_TOKEN = get_ajax_token(self.session)
        logger.info(f"AJAX token: {AJAX_TOKEN[:10]}...")

        password_md5 = hashlib.md5(PASSWORD.encode()).hexdigest()

        # First attempt without captcha
        result = self._ajax("account/login", {
            "username": USERNAME,
            "password": password_md5,
        })

        # If captcha required, solve it
        if result.get("data", {}).get("requireCaptcha"):
            logger.info("Captcha required, solving...")
            hcaptcha_token = self._solve_hcaptcha()
            if not hcaptcha_token:
                logger.error("Failed to solve hCaptcha")
                return False

            result = self._ajax("account/login", {
                "username": USERNAME,
                "password": password_md5,
                "hcaptcha": hcaptcha_token,
            })

        if result.get("success"):
            self.logged_in = True
            logger.info(f"✅ Login successful as {USERNAME}")
            return True

        logger.error(f"❌ Login failed: {result}")
        return False

    def keep_alive(self) -> bool:
        """Visit the servers page to keep the account active."""
        resp = self.session.get(f"{self.BASE_URL}/servers/")
        if resp.status_code == 200 and "login" not in resp.url.lower():
            logger.info("✅ Panel visit successful — server kept alive")
            return True
        logger.warning(f"⚠️ Panel visit may have failed: {resp.status_code}")
        return False

    def renew(self) -> bool:
        """Full renewal cycle: login + keep alive."""
        if not USERNAME or not PASSWORD:
            logger.error("ATERNOS_USERNAME and ATERNOS_PASSWORD must be set")
            return False

        if not self.login():
            return False

        return self.keep_alive()


def main():
    if not USERNAME or not PASSWORD:
        logger.error("ATERNOS_USERNAME and ATERNOS_PASSWORD must be set")
        sys.exit(1)

    client = AternosClient()
    success = client.renew()
    if success:
        logger.info("🎉 Renewal complete!")
    else:
        # Don't exit with error — captcha may clear on next run
        logger.warning("⚠️ Renewal failed, will retry in 6 hours")


if __name__ == "__main__":
    main()
