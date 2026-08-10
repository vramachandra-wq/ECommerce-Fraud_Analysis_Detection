"""CLI: python -m notifications  → send one backlog digest now."""

from __future__ import annotations

import json
import logging
import sys

from notifications.backlog_digest import send_backlog_digest

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
)


def main() -> int:
    result = send_backlog_digest(force=True)
    print(json.dumps(result, indent=2, default=str))
    if result.get("skipped"):
        return 1
    return 0 if result.get("sent") else 2


if __name__ == "__main__":
    sys.exit(main())
