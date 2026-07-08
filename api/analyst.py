from fastapi import APIRouter, Request
import psycopg2
from config import DB_CONFIG

router = APIRouter()

# approve order
@router.put("/approve-order")
async def approve_order(request: Request):

    data = await request.json()

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

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
            data["approved_at"],
            data["reviewed_by"],
            data["review_comments"],
            data["order_id"],
        ),
    )

    conn.commit()

    cur.close()
    conn.close()

    return {"message":"Approved"}

#reject order
@router.put("/reject-order")
async def reject_order(request: Request):

    data = await request.json()

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE master.orders
        SET order_status='REJECTED',
            is_fraud=TRUE,
            order_rejected_at=%s,
            reviewed_by=%s,
            review_comments=%s
        WHERE order_id=%s
        """,
        (
            data["rejected_at"],
            data["reviewed_by"],
            data["review_comments"],
            data["order_id"],
        ),
    )

    conn.commit()

    cur.close()
    conn.close()

    return {"message":"Rejected"}

#batch approve

@router.put("/batch-approve")
async def batch_approve(request: Request):

    data = await request.json()

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

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
            data["approved_at"],
            data["reviewed_by"],
            data["review_comments"],
            data["order_ids"],
        ),
    )

    conn.commit()

    cur.close()
    conn.close()

    return {"message":"Batch Approved"}

#batch reject

@router.put("/batch-reject")
async def batch_reject(request: Request):

    data = await request.json()

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE master.orders
        SET order_status='REJECTED',
            is_fraud=TRUE,
            order_rejected_at=%s,
            reviewed_by=%s,
            review_comments=%s
        WHERE order_id = ANY(%s)
        """,
        (
            data["rejected_at"],
            data["reviewed_by"],
            data["review_comments"],
            data["order_ids"],
        ),
    )

    conn.commit()

    cur.close()
    conn.close()

    return {"message":"Batch Rejected"}