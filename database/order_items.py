"""Order line-items schema helpers (multi-product orders)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

ORDER_ITEMS_DDL = """
CREATE TABLE IF NOT EXISTS master.order_items (
    order_item_id BIGSERIAL PRIMARY KEY,
    order_id      VARCHAR(20)  NOT NULL,
    line_no       INTEGER      NOT NULL,
    product_id    VARCHAR(64)  NOT NULL,
    product_name  VARCHAR(255) NOT NULL,
    category      VARCHAR(128),
    quantity      INTEGER      NOT NULL CHECK (quantity >= 1),
    unit_price    NUMERIC(12, 2) NOT NULL,
    line_amount   NUMERIC(12, 2) NOT NULL,
    line_status   VARCHAR(32),
    flagged_reason TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

ORDER_ITEMS_INDEX_DDL = """
CREATE INDEX IF NOT EXISTS idx_order_items_order_id
    ON master.order_items (order_id);
"""

ORDER_ITEMS_ALTER_DDL = [
    "ALTER TABLE master.order_items ADD COLUMN IF NOT EXISTS line_status VARCHAR(32)",
    "ALTER TABLE master.order_items ADD COLUMN IF NOT EXISTS flagged_reason TEXT",
]


def ensure_order_items_table(cur) -> None:
    """Create master.order_items if missing (safe to call repeatedly)."""
    cur.execute(ORDER_ITEMS_DDL)
    cur.execute(ORDER_ITEMS_INDEX_DDL)
    for stmt in ORDER_ITEMS_ALTER_DDL:
        cur.execute(stmt)


def insert_order_items(
    cur,
    order_id: str,
    lines: Sequence[Dict[str, Any]],
) -> None:
    """
    Persist order line items.

    Each line dict must include:
      product_id, product_name, category, quantity, unit_price, line_amount
    Optional: line_status, flagged_reason
    """
    rows: List[Tuple[Any, ...]] = []
    for i, line in enumerate(lines, start=1):
        rows.append(
            (
                order_id,
                i,
                line["product_id"],
                line["product_name"],
                line.get("category"),
                int(line["quantity"]),
                float(line["unit_price"]),
                float(line["line_amount"]),
                line.get("line_status"),
                line.get("flagged_reason"),
            )
        )
    from psycopg2.extras import execute_batch

    execute_batch(
        cur,
        """
        INSERT INTO master.order_items (
            order_id, line_no, product_id, product_name, category,
            quantity, unit_price, line_amount, line_status, flagged_reason
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        rows,
    )


def fetch_order_items(cur, order_id: str) -> List[Dict[str, Any]]:
    cur.execute(
        """
        SELECT order_item_id, line_no, product_id, product_name, category,
               quantity, unit_price, line_amount, line_status, flagged_reason
        FROM master.order_items
        WHERE order_id = %s
        ORDER BY line_no
        """,
        (order_id,),
    )
    cols = [
        "order_item_id",
        "line_no",
        "product_id",
        "product_name",
        "category",
        "quantity",
        "unit_price",
        "line_amount",
        "line_status",
        "flagged_reason",
    ]
    out: List[Dict[str, Any]] = []
    for row in cur.fetchall():
        item = dict(zip(cols, row))
        item["unit_price"] = float(item["unit_price"])
        item["line_amount"] = float(item["line_amount"])
        item["quantity"] = int(item["quantity"])
        out.append(item)
    return out


def fetch_order_rule_hits(cur, order_id: str) -> List[Dict[str, Any]]:
    cur.execute(
        """
        SELECT rule_id, rule_name, rule_description
        FROM master.order_rule_hits
        WHERE order_id = %s
        ORDER BY hit_id
        """,
        (order_id,),
    )
    return [
        {
            "rule_id": r[0],
            "rule_name": r[1],
            "rule_description": r[2],
        }
        for r in cur.fetchall()
    ]


def header_summary(lines: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build backward-compatible orders-header fields from line items.
    Existing analyst/UI columns still expect one product_* on master.orders.
    """
    if not lines:
        raise ValueError("lines required")
    first = lines[0]
    total_qty = sum(int(l["quantity"]) for l in lines)
    total_amount = round(sum(float(l["line_amount"]) for l in lines), 2)
    if len(lines) == 1:
        product_name = first["product_name"]
        category = first.get("category")
    else:
        product_name = f"{first['product_name']} (+{len(lines) - 1} more)"
        cats = {l.get("category") for l in lines if l.get("category")}
        category = next(iter(cats)) if len(cats) == 1 else "MULTI"
    return {
        "product_id": first["product_id"],
        "product_name": product_name,
        "category": category,
        "quantity": total_qty,
        "amount": total_amount,
    }


def enrich_order_with_items(cur, order: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Attach ``items``, ``item_count``, and ``triggered_rules`` to an order dict.
    Legacy single-product rows (no order_items) get a synthetic one-line list.
    """
    if not order:
        return order
    try:
        ensure_order_items_table(cur)
        items = fetch_order_items(cur, str(order.get("order_id") or ""))
        triggered = fetch_order_rule_hits(cur, str(order.get("order_id") or ""))
    except Exception:
        items = []
        triggered = []

    if not items and order.get("product_id"):
        qty = int(order.get("quantity") or 1)
        amount = float(order.get("amount") or 0)
        unit = round(amount / qty, 2) if qty else amount
        items = [
            {
                "order_item_id": None,
                "line_no": 1,
                "product_id": order.get("product_id"),
                "product_name": order.get("product_name"),
                "category": order.get("category"),
                "quantity": qty,
                "unit_price": unit,
                "line_amount": amount,
                "line_status": order.get("order_status"),
                "flagged_reason": order.get("flagged_reason"),
            }
        ]

    order["items"] = items
    order["item_count"] = len(items)
    order["triggered_rules"] = triggered
    return order
