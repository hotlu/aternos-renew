"""
Aternos server auto-renewal script.
Uses SeleniumBase with undetected Chrome to bypass Cloudflare and hCaptcha.
"""

import os
import sys
import time
import hashlib
import re
import logging
from datetime import datetime, timezone, timedelta

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

USERNAME = os.environ.get("ATERNOS_USERNAME", "")
PASSWORD = os.environ.get("ATERNOS_PASSWORD", "")
BASE_URL = "https://aternos.org"
STATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser_state")
SCREENSHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")

os.makedirs(STATE_DIR, exist_ok=True)
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

AJAX_TOKEN = "Kg5pUrtEcWixTBzGuE51"


def take_screenshot(driver, name):
    timestamp = datetime.now().strftime('%H%M%S')
    filename = f"{SCREENSHOT_DIR}/{timestamp}-{name}.png"
    try:
        driver.save_screenshot(filename)
        logger.info(f"📸 Screenshot: {filename}")
    except Exception as e:
        logger.warning(f"Screenshot failed: {e}")
    return filename


def wait_for_url_contains(driver, keyword, timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        if keyword in driver.current_url:
            return True
        time.sleep(0.5)
    return False


def check_login_error(driver):
    try:
        body = driver.execute_script("return document.body.innerText")
        if "incorrect" in body.lower() or "invalid" in body.lower():
            return body[:200]
    except:
        pass
    return None


def main():
    if not USERNAME or not PASSWORD:
        logger.error("ATERNOS_USERNAME and ATERNOS_PASSWORD must be set")
        sys.exit(1)

    logger.info("=" * 50)
    logger.info("Aternos Auto Renew (SeleniumBase)")
    logger.info("=" * 50)

    try:
        from seleniumbase import Driver
    except ImportError:
        logger.error("seleniumbase not installed. Run: pip install seleniumbase")
        sys.exit(1)

    # Browser config
    driver_kwargs = {
        "headless": True,
        "headless2": True,
        "uc": True,
        "user_data_dir": STATE_DIR,
        "window_size": "1280,753",
        "disable_csp": True,
    }

    driver = Driver(**driver_kwargs)
    driver.set_page_load_timeout(60)
    driver.set_script_timeout(60)

    try:
        # 1. Visit login page
        logger.info(f"🌐 Visiting {BASE_URL}/go")
        driver.get(f"{BASE_URL}/go")

        # Wait for Cloudflare challenge to resolve
        logger.info("⏳ Waiting for Cloudflare challenge...")
        for i in range(60):
            time.sleep(3)
            body = driver.execute_script("return document.body.innerText")
            if "just a moment" not in body.lower() and "security verification" not in body.lower() and "verif" not in body.lower():
                logger.info(f"✅ Cloudflare passed (attempt {i+1})")
                break
            # Try clicking Turnstile/Cloudflare checkbox every 5 attempts
            if i % 5 == 0:
                try:
                    driver.uc_gui_click_cf()
                    logger.info(f"Clicked Cloudflare checkbox (attempt {i+1})")
                except:
                    # Try clicking iframe directly
                    try:
                        driver.execute_script('''
                            var iframe = document.querySelector("iframe[src*='challenges']");
                            if(iframe) { iframe.click(); }
                        ''')
                    except:
                        pass
        else:
            take_screenshot(driver, "ERROR-cloudflare-timeout")
            raise Exception("Cloudflare challenge timeout")

        time.sleep(3)
        take_screenshot(driver, "01-login-page")

        # Debug: check what's on the page
        page_url = driver.current_url
        page_text = driver.execute_script("return document.body.innerText")
        page_html_len = driver.execute_script("return document.documentElement.outerHTML.length")
        logger.info(f"URL: {page_url}")
        logger.info(f"HTML length: {page_html_len}")
        logger.info(f"Page text: {page_text[:300]}")

        # Wait for login form to appear
        logger.info("⏳ Waiting for login form...")
        for i in range(20):
            if driver.is_element_present("input.username") or driver.is_element_present("input[type='password']"):
                logger.info(f"✅ Login form found (attempt {i+1})")
                break
            time.sleep(2)
        else:
            take_screenshot(driver, "ERROR-no-login-form")
            raise Exception(f"Login form not found. Page text: {page_text[:200]}")

        # 2. Check if already logged in
        if "/go" not in driver.current_url and "login" not in driver.current_url.lower():
            logger.info("✅ Already logged in")
        else:
            # 3. Fill login form
            logger.info("✍️ Filling login form")
            username_input = driver.find_element("input.username, input[placeholder*='Username']")
            username_input.clear()
            username_input.send_keys(USERNAME)

            password_input = driver.find_element("input.password, input[type='password']")
            password_input.clear()
            password_input.send_keys(PASSWORD)
            take_screenshot(driver, "02-credentials")

            # 4. Check for hCaptcha
            time.sleep(3)
            if driver.is_element_present("iframe[src*='hcaptcha']"):
                logger.info("🔒 hCaptcha detected, attempting to solve...")
                try:
                    # Try SeleniumBase's built-in hcaptcha solver
                    driver.uc_gui_click_hcaptcha("iframe[src*='hcaptcha']")
                    logger.info("✅ hCaptcha clicked")
                except Exception as e:
                    logger.warning(f"hCaptcha click failed: {e}")
                    # Try alternative: click the checkbox directly
                    try:
                        driver.execute_script(
                            "document.querySelector('iframe[src*=\"hcaptcha\"]').click()"
                        )
                    except:
                        pass

                time.sleep(10)
                take_screenshot(driver, "03-hcaptcha")

                # Check if captcha was solved
                # Wait for the captcha response
                for i in range(30):
                    has_token = driver.execute_script(
                        'return !!document.querySelector("[name=h-captcha-response]")?.value'
                    )
                    if has_token:
                        logger.info("✅ hCaptcha solved!")
                        break
                    time.sleep(2)
                else:
                    logger.warning("⚠️ hCaptcha may not be solved, trying anyway...")

            # 5. Click login button
            logger.info("🚀 Clicking login button")
            login_btn = driver.find_element("button")
            for btn in driver.find_elements("button"):
                try:
                    text = btn.text.strip().lower()
                    if "login" in text or "sign in" in text:
                        login_btn = btn
                        break
                except:
                    pass
            login_btn.click()
            take_screenshot(driver, "04-login-clicked")

            # 6. Wait for redirect
            logger.info("⏳ Waiting for login redirect...")
            if wait_for_url_contains(driver, "/servers", timeout=30):
                logger.info("✅ Login successful!")
            else:
                error = check_login_error(driver)
                if error:
                    logger.error(f"❌ Login failed: {error}")
                else:
                    # Check current URL
                    url = driver.current_url
                    logger.warning(f"⚠️ Unexpected URL: {url}")
                    if "go" in url and "login" not in url:
                        # Might have redirected somewhere else
                        pass
                take_screenshot(driver, "ERROR-login")

        # 7. Visit servers page to keep alive
        logger.info("📡 Visiting servers page...")
        driver.get(f"{BASE_URL}/servers/")
        time.sleep(5)
        take_screenshot(driver, "05-servers")

        body_text = driver.execute_script("return document.body.innerText")
        if "login" not in driver.current_url.lower():
            logger.info("✅ Panel visit successful — server kept alive!")
            logger.info(f"Page content: {body_text[:200]}")
        else:
            logger.warning("⚠️ May not be logged in")

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        take_screenshot(driver, "ERROR-unknown")
        sys.exit(1)
    finally:
        driver.quit()

    logger.info("🎉 Renewal complete!")


if __name__ == "__main__":
    main()
