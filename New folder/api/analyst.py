from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from config import DB_CONFIG

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


# --- ENDPOINTS ---

@router.put("/approve-order")
def approve_order(data: ApproveOrderRequest):
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE master.orders
                    SET order_status='APPROVED',
                        is_fraud=FALSE,
                        order_approved_at=%s,
                        reviewed_by=%s,
                        review_comments=%s
                    WHERE order_id=%s
                    """,
                    (
                        data.approved_at,
                        data.reviewed_by,
                        data.review_comments,
                        data.order_id,
                    ),
                )
        return {"message": "Approved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/reject-order")
def reject_order(data: RejectOrderRequest):
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE master.orders
                    SET order_status='REJECTED',
                        is_fraud=%s,
                        order_rejected_at=%s,
                        reviewed_by=%s,
                        review_comments=%s
                    WHERE order_id=%s
                    """,
                    (
                        data.is_fraud,
                        data.rejected_at,
                        data.reviewed_by,
                        data.review_comments,
                        data.order_id,
                    ),
                )
        return {"message": "Rejected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/batch-approve")
def batch_approve(data: BatchApproveRequest):
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE master.orders
                    SET order_status='APPROVED',
                        is_fraud=FALSE,
                        order_approved_at=%s,
                        reviewed_by=%s,
                        review_comments=%s
                    WHERE order_id = ANY(%s)
                    """,
                    (
                        data.approved_at,
                        data.reviewed_by,
                        data.review_comments,
                        data.order_ids,
                    ),
                )
        return {"message": f"Batch Approved {len(data.order_ids)} orders"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/batch-reject")
def batch_reject(data: BatchRejectRequest):
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE master.orders
                    SET order_status='REJECTED',
                        is_fraud=%s,
                        order_rejected_at=%s,
                        reviewed_by=%s,
                        review_comments=%s
                    WHERE order_id = ANY(%s)
                    """,
                    (
                        data.is_fraud,
                        data.rejected_at,
                        data.reviewed_by,
                        data.review_comments,
                        data.order_ids,
                    ),
                )
        return {"message": f"Batch Rejected {len(data.order_ids)} orders"}
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