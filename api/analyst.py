from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
import psycopg2
from psycopg2.extras import RealDictCursor
from config import DB_CONFIG
from fraud_engine.audit import fetch_order_audit_context, log_review_action

router = APIRouter()

# --- PYDANTIC MODELS ---

class ApproveOrderRequest(BaseModel):
    order_id: str
    approved_at: str
    reviewed_by: str
    review_comments: str

class RejectOrderRequest(BaseModel):
    order_id: str
    rejected_at: str
    reviewed_by: str
    review_comments: str
    is_fraud: bool = True  # Defaults to True if omitted

class BatchApproveRequest(BaseModel):
    order_ids: List[str]
    approved_at: str
    reviewed_by: str
    review_comments: str

class BatchRejectRequest(BaseModel):
    order_ids: List[str]
    rejected_at: str
    reviewed_by: str
    review_comments: str
    is_fraud: bool = True


def _lock_and_update_approve(cur, order_id: str, approved_at: str, reviewed_by: str, comments: str) -> bool:
    """Approve a single order with row lock; returns False if already resolved."""
    cur.execute(
        """
        SELECT order_id FROM master.orders
        WHERE order_id = %s
          AND order_status IN ('ON_HOLD', 'PENDING_REVIEW')
        FOR UPDATE SKIP LOCKED
        """,
        (order_id,),
    )
    if not cur.fetchone():
        return False

    ctx = fetch_order_audit_context(cur, order_id)
    cur.execute(
        """
        UPDATE master.orders
        SET order_status='APPROVED',
            is_fraud=FALSE,
            order_approved_at=%s,
            reviewed_by=%s,
            review_comments=%s
        WHERE order_id=%s
          AND order_status IN ('ON_HOLD', 'PENDING_REVIEW')
        """,
        (approved_at, reviewed_by, comments, order_id),
    )
    if cur.rowcount != 1:
        return False

    log_review_action(
        cur,
        order_id=order_id,
        action="APPROVE",
        reason="Manual",
        analyst_id=reviewed_by,
        rule_name=ctx.get("rule_name"),
        delay_minutes=ctx.get("delay_minutes"),
        review_comments=comments,
    )
    return True


def _lock_and_update_reject(
    cur, order_id: str, rejected_at: str, reviewed_by: str, comments: str, is_fraud: bool
) -> bool:
    """Reject / mark-fraud with row lock; returns False if already resolved."""
    cur.execute(
        """
        SELECT order_id FROM master.orders
        WHERE order_id = %s
          AND order_status IN ('ON_HOLD', 'PENDING_REVIEW')
        FOR UPDATE SKIP LOCKED
        """,
        (order_id,),
    )
    if not cur.fetchone():
        return False

    ctx = fetch_order_audit_context(cur, order_id)
    cur.execute(
        """
        UPDATE master.orders
        SET order_status='REJECTED',
            is_fraud=%s,
            order_rejected_at=%s,
            reviewed_by=%s,
            review_comments=%s
        WHERE order_id=%s
          AND order_status IN ('ON_HOLD', 'PENDING_REVIEW')
        """,
        (is_fraud, rejected_at, reviewed_by, comments, order_id),
    )
    if cur.rowcount != 1:
        return False

    action = "MARK_FRAUD" if is_fraud else "REJECT"
    log_review_action(
        cur,
        order_id=order_id,
        action=action,
        reason="Manual",
        analyst_id=reviewed_by,
        rule_name=ctx.get("rule_name"),
        delay_minutes=ctx.get("delay_minutes"),
        review_comments=comments,
    )
    return True


# --- ENDPOINTS ---

@router.put("/approve-order")
def approve_order(data: ApproveOrderRequest):
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                ok = _lock_and_update_approve(
                    cur,
                    data.order_id,
                    data.approved_at,
                    data.reviewed_by,
                    data.review_comments,
                )
                if not ok:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Order {data.order_id} is no longer in the review queue.",
                    )
        return {"message": "Approved"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/reject-order")
def reject_order(data: RejectOrderRequest):
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                ok = _lock_and_update_reject(
                    cur,
                    data.order_id,
                    data.rejected_at,
                    data.reviewed_by,
                    data.review_comments,
                    data.is_fraud,
                )
                if not ok:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Order {data.order_id} is no longer in the review queue.",
                    )
        return {"message": "Rejected"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/batch-approve")
def batch_approve(data: BatchApproveRequest):
    try:
        processed = []
        skipped = []
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                for order_id in data.order_ids:
                    ok = _lock_and_update_approve(
                        cur,
                        order_id,
                        data.approved_at,
                        data.reviewed_by,
                        data.review_comments,
                    )
                    if ok:
                        processed.append(order_id)
                    else:
                        skipped.append(order_id)
        return {
            "message": f"Batch Approved {len(processed)} orders",
            "processed": processed,
            "skipped": skipped,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/batch-reject")
def batch_reject(data: BatchRejectRequest):
    try:
        processed = []
        skipped = []
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                for order_id in data.order_ids:
                    ok = _lock_and_update_reject(
                        cur,
                        order_id,
                        data.rejected_at,
                        data.reviewed_by,
                        data.review_comments,
                        data.is_fraud,
                    )
                    if ok:
                        processed.append(order_id)
                    else:
                        skipped.append(order_id)
        return {
            "message": f"Batch Rejected {len(processed)} orders",
            "processed": processed,
            "skipped": skipped,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pending-reviews")
def get_pending_reviews():
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        order_id, order_timestamp, amount, order_status,
                        flagged_reason, delay_minutes
                    FROM master.orders
                    WHERE order_status IN ('PENDING_REVIEW', 'ON_HOLD')
                    ORDER BY order_timestamp ASC
                    """
                )
                orders = cur.fetchall()
        return {"data": orders}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
