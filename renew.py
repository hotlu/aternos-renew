"""
Aternos server auto-renewal script.
Uses SeleniumBase UC Mode + Xvfb to bypass Cloudflare.
Reference: https://github.com/1837620622/cloudflare-bypass-2026
"""

import os
import sys
import time
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

USERNAME = os.environ.get("ATERNOS_USERNAME", "")
PASSWORD = os.environ.get("ATERNOS_PASSWORD", "")
BASE_URL = "https://aternos.org"


def setup_display():
    """Setup Xvfb virtual display on Linux."""
    import platform
    if platform.system().lower() == "linux" and not os.environ.get("DISPLAY"):
        try:
            from pyvirtualdisplay import Display
            display = Display(visible=False, size=(1920, 1080))
            display.start()
            os.environ["DISPLAY"] = display.new_display_var
            logger.info("🖥️ Xvfb virtual display started")
            return display
        except Exception as e:
            logger.error(f"Failed to start Xvfb: {e}")
            return None
    return None


def main():
    if not USERNAME or not PASSWORD:
        logger.error("ATERNOS_USERNAME and ATERNOS_PASSWORD must be set")
        sys.exit(1)

    logger.info("=" * 50)
    logger.info("Aternos Auto Renew (SeleniumBase UC Mode)")
    logger.info("=" * 50)

    # Setup virtual display for Linux
    display = setup_display()

    try:
        from seleniumbase import SB
    except ImportError:
        logger.error("seleniumbase not installed. Run: pip install seleniumbase")
        sys.exit(1)

    try:
        with SB(uc=True, test=True, locale="en") as sb:
            # 1. Visit login page with reconnection
            logger.info(f"🌐 Visiting {BASE_URL}/go")
            sb.uc_open_with_reconnect(f"{BASE_URL}/go", reconnect_time=8.0)
            time.sleep(3)

            # 2. Check if Cloudflare challenge is present
            page_source = sb.get_page_source().lower()
            cf_indicators = ["turnstile", "challenges.cloudflare", "just a moment",
                             "verify you are human", "security verification"]

            if any(x in page_source for x in cf_indicators):
                logger.info("🔒 Cloudflare challenge detected, solving...")
                try:
                    sb.uc_gui_click_captcha()
                    logger.info("✅ Clicked Cloudflare captcha")
                except Exception as e:
                    logger.warning(f"Click failed: {e}")

                # Wait for challenge to resolve
                for i in range(30):
                    time.sleep(3)
                    body = sb.execute_script("return document.body.innerText").lower()
                    if "just a moment" not in body and "security verification" not in body:
                        logger.info(f"✅ Cloudflare passed (attempt {i+1})")
                        break
                    if i % 5 == 0:
                        try:
                            sb.uc_gui_click_captcha()
                        except:
                            pass
                else:
                    logger.error("❌ Cloudflare challenge timeout")
                    return

            # Wait for cookies to be set after Cloudflare
            logger.info("⏳ Waiting for cookies to settle...")
            time.sleep(8)

            # Reload the page to ensure cookies are active
            sb.uc_open_with_reconnect(f"{BASE_URL}/go", reconnect_time=5.0)
            time.sleep(5)

            time.sleep(3)

            # 3. Check if already logged in
            current_url = sb.execute_script("return window.location.href")
            if "/go" not in current_url and "login" not in current_url.lower():
                logger.info("✅ Already logged in")
            else:
                # 4. Fill login form
                logger.info("✍️ Filling login form")

                # Wait for form to appear
                for i in range(20):
                    if sb.is_element_present("input.username") or sb.is_element_present("input[type='password']"):
                        break
                    time.sleep(2)
                else:
                    body_text = sb.execute_script("return document.body.innerText")[:300]
                    logger.error(f"❌ Login form not found. Page: {body_text}")
                    return

                sb.type("input.username, input[placeholder*='Username']", USERNAME)
                time.sleep(1)
                sb.type("input.password, input[type='password']", PASSWORD)
                time.sleep(3)

                # 5. Check for hCaptcha
                if sb.is_element_present("iframe[src*='hcaptcha']"):
                    logger.info("🔒 hCaptcha detected, solving...")
                    try:
                        sb.uc_gui_click_captcha()
                        time.sleep(10)
                    except Exception as e:
                        logger.warning(f"hCaptcha click failed: {e}")

                # 6. Click login
                logger.info("🚀 Clicking login button")
                # Try multiple selectors for the login button
                clicked = False
                for selector in ['button.login-button', 'button[type="submit"]', 'button']:
                    try:
                        if sb.is_element_present(selector):
                            sb.click(selector)
                            clicked = True
                            logger.info(f"Clicked: {selector}")
                            break
                    except:
                        pass
                if not clicked:
                    # Try JavaScript click
                    sb.execute_script("document.querySelector('button').click()")
                time.sleep(10)

                # 7. Wait for redirect
                for i in range(30):
                    current_url = sb.execute_script("return window.location.href")
                    if "/go" not in current_url and "login" not in current_url.lower():
                        logger.info("✅ Login successful!")
                        break
                    time.sleep(2)
                else:
                    body_text = sb.execute_script("return document.body.innerText")[:300]
                    logger.error(f"❌ Login failed. Page: {body_text}")
                    return

            # 8. Visit servers page
            logger.info("📡 Visiting servers page...")
            sb.uc_open_with_reconnect(f"{BASE_URL}/servers/", reconnect_time=5.0)
            time.sleep(5)

            current_url = sb.execute_script("return window.location.href")
            body_text = sb.execute_script("return document.body.innerText")[:300]

            if "login" not in current_url.lower():
                logger.info("✅ Panel visit successful — server kept alive!")
                logger.info(f"Page: {body_text[:200]}")
            else:
                logger.warning(f"⚠️ May not be logged in. URL: {current_url}")

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        if display:
            display.stop()

    logger.info("🎉 Renewal complete!")


if __name__ == "__main__":
    main()
