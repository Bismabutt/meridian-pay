"""Database connection helper."""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool

from app.config import settings

_pool = None


def init_pool():
    global _pool
    if _pool is None:
        _pool = SimpleConnectionPool(
            1, 10,
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            dbname=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
        )
    return _pool


def get_conn():
    return init_pool().getconn()


def put_conn(conn):
    init_pool().putconn(conn)


def query(sql, params=None, fetch="all"):
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params or ())
            if fetch == "one":
                row = cur.fetchone()
            elif fetch == "all":
                row = cur.fetchall()
            else:
                row = None
            conn.commit()
            return row
    except Exception:
        conn.rollback()
        raise
    finally:
        put_conn(conn)
