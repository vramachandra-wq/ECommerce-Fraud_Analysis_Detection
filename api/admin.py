from fastapi import APIRouter, Request
import psycopg2
from config import DB_CONFIG

router = APIRouter()


@router.post("/create-analyst")
async def create_analyst(request: Request):

    data = await request.json()

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO master.analyst_users
        (analyst_id, employee_name, username, password, role)
        VALUES (%s,%s,%s,%s,%s)
        """,
        (
            data["analyst_id"],
            data["employee_name"],
            data["username"],
            data["password"],
            data["role"],
        ),
    )

    conn.commit()

    cur.close()
    conn.close()

    return {"message": "Analyst Created"}

@router.post("/blacklist-ip")
async def blacklist_ip(request: Request):

    data = await request.json()

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO master.ip_blacklist (ip_address, reason, blacklisted_by)
        VALUES (%s,%s,%s)
        """,
        (
            data["ip_address"],
            data["reason"],
            data["blacklisted_by"],
        ),
    )

    conn.commit()
    cur.close()
    conn.close()

    return {"message": "IP Blacklisted"}

@router.put("/whitelist-ip")
async def whitelist_ip(request: Request):

    data = await request.json()

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE master.ip_blacklist
        SET is_active = FALSE,
            removed_by = %s,
            removed_at = %s
        WHERE blacklist_id = %s
        """,
        (
            data["removed_by"],
            data["removed_at"],
            data["blacklist_id"],
        ),
    )

    conn.commit()

    cur.close()
    conn.close()

    return {"message":"Whitelisted"}

@router.put("/permissions")
async def update_permissions(request: Request):

    data = await request.json()

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO master.analyst_permissions
        (analyst_id,page_key,granted,granted_by,granted_at)
        VALUES (%s,%s,%s,%s,%s)
        ON CONFLICT (analyst_id,page_key)
        DO UPDATE SET
            granted=EXCLUDED.granted,
            granted_by=EXCLUDED.granted_by,
            granted_at=EXCLUDED.granted_at
        """,
        (
            data["analyst_id"],
            data["page_key"],
            data["granted"],
            data["granted_by"],
            data["granted_at"],
        ),
    )

    conn.commit()

    cur.close()
    conn.close()

    return {"message":"Permission Updated"}