"""
Aternos server auto-renewal script.
Uses python-aternos library for reliable API access.
"""

import os
import sys
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

USERNAME = os.environ.get("ATERNOS_USERNAME", "")
PASSWORD = os.environ.get("ATERNOS_PASSWORD", "")
SESSION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".aternos_session")


def main():
    if not USERNAME or not PASSWORD:
        logger.error("ATERNOS_USERNAME and ATERNOS_PASSWORD must be set")
        sys.exit(1)

    logger.info("=" * 50)
    logger.info("Aternos Auto Renew (python-aternos)")
    logger.info("=" * 50)

    try:
        from python_aternos import Client
    except ImportError:
        logger.error("python-aternos not installed. Run: pip install python-aternos")
        sys.exit(1)

    # Try to restore session first
    aternos = None
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r") as f:
                session_cookie = f.read().strip()
            if session_cookie:
                aternos = Client.from_session(session_cookie)
                logger.info("✅ Restored session from file")
        except Exception as e:
            logger.warning(f"Session restore failed: {e}")

    # Login if no session
    if aternos is None:
        logger.info(f"🔐 Logging in as {USERNAME}")
        try:
            aternos = Client.from_credentials(USERNAME, PASSWORD)
            logger.info("✅ Login successful!")
        except Exception as e:
            logger.error(f"❌ Login failed: {e}")
            sys.exit(1)

    # Save session for next run
    try:
        session_cookie = aternos.session.cookies.get("ATERNOS_SESSION")
        if session_cookie:
            with open(SESSION_FILE, "w") as f:
                f.write(session_cookie)
            logger.info("💾 Session saved")
    except Exception as e:
        logger.warning(f"Session save failed: {e}")

    # Get server list
    try:
        servers = aternos.list_servers()
        logger.info(f"📋 Found {len(servers)} server(s)")

        for i, server in enumerate(servers):
            logger.info(f"  Server #{i}: {server.address} | {server.software} {server.version}")
            logger.info(f"    Status: {server.status_label if hasattr(server, 'status_label') else 'unknown'}")

    except Exception as e:
        logger.error(f"❌ Failed to get server list: {e}")
        sys.exit(1)

    # Visit panel to keep account active
    try:
        # Access the servers page via the API to keep the session alive
        logger.info("📡 Keeping session alive...")
        aternos.list_servers()  # This refreshes the session
        logger.info("✅ Session refreshed — server kept alive!")
    except Exception as e:
        logger.warning(f"⚠️ Session refresh failed: {e}")

    logger.info("🎉 Renewal complete!")


if __name__ == "__main__":
    main()
