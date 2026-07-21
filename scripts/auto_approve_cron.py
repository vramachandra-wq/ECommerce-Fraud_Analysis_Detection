#!/usr/bin/env python3
"""Standalone cron entrypoint for auto-approving expired ON_HOLD orders.

This is OPTIONAL background sync — the in-app sync (analyst/admin portal, on
render) already auto-approves expired holds, so this script only matters if
you want orders cleared even while nobody is logged into the portal.

Crontab example (every 5 minutes), enable only if desired:
    */5 * * * * /usr/bin/python3 /path/to/scripts/auto_approve_cron.py >> /var/log/metrocart_auto_approve.log 2>&1

Toggle on/off without touching crontab:
    AUTO_APPROVAL_CRON_ENABLED=false   (in .env or environment)
"""
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg2

from config import DB_CONFIG
from fraud_engine.auto_approval import sync_expired_holds

logging.basicConfig(level=logging.INFO, format="%(asctime)s [auto-approve-cron] %(message)s")
logger = logging.getLogger(__name__)


def _is_enabled() -> bool:
    return os.environ.get("AUTO_APPROVAL_CRON_ENABLED", "true").strip().lower() not in ("false", "0", "no")


def main() -> int:
    if not _is_enabled():
        logger.info("Skipped — AUTO_APPROVAL_CRON_ENABLED is false")
        return 0

    conn = psycopg2.connect(**DB_CONFIG)
    try:
        cur = conn.cursor()
        try:
            approved = sync_expired_holds(conn, cur)
            conn.commit()
            logger.info("Auto-approved %d expired order(s)", approved)
        finally:
            cur.close()
    except Exception:
        conn.rollback()
        logger.exception("Auto-approval cron run failed")
        return 1
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
