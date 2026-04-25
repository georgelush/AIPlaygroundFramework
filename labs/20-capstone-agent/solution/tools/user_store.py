"""
Postgres-backed user store for HR Assistant admin operations.
Stores user_id -> role mappings used by RBAC.
"""

from __future__ import annotations

from threading import Lock
import os

try:
    import psycopg
except ImportError:  # pragma: no cover
    psycopg = None

from src.config import POSTGRES_URL

_ALLOWED_ROLES = {"guest", "employee", "manager", "admin"}

_conn_lock = Lock()
_conn = None
_schema_ready = False
_bootstrap_done = False


def _get_conn():
    if psycopg is None:
        raise RuntimeError("psycopg is not installed. Run: pip install -r requirements.txt")
    global _conn
    with _conn_lock:
        if _conn is None or _conn.closed:
            _conn = psycopg.connect(POSTGRES_URL, autocommit=True)
    return _conn


def ensure_schema() -> None:
    global _schema_ready
    if _schema_ready:
        return
    conn = _get_conn()
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS hr_users (
                user_id TEXT PRIMARY KEY,
                role TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        # Backward-compatible migration for older table definitions.
        cur.execute(
            "ALTER TABLE hr_users ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"
        )
        cur.execute(
            "ALTER TABLE hr_users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"
        )
    _schema_ready = True


def seed_users(users: dict[str, str]) -> None:
    ensure_schema()
    conn = _get_conn()
    with conn.cursor() as cur:
        for user_id, role in users.items():
            if role not in _ALLOWED_ROLES:
                continue
            cur.execute(
                """
                INSERT INTO hr_users (user_id, role)
                VALUES (%s, %s)
                ON CONFLICT (user_id) DO NOTHING
                """,
                (user_id.lower(), role),
            )


def get_user_role(user_id: str) -> str | None:
    ensure_schema()
    conn = _get_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT role FROM hr_users WHERE user_id = %s", (user_id.lower(),))
        row = cur.fetchone()
    return row[0] if row else None


def upsert_user_role(user_id: str, role: str) -> None:
    if role not in _ALLOWED_ROLES:
        raise ValueError(f"Invalid role '{role}'. Allowed: {sorted(_ALLOWED_ROLES)}")
    ensure_schema()
    conn = _get_conn()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO hr_users (user_id, role)
            VALUES (%s, %s)
            ON CONFLICT (user_id)
            DO UPDATE SET role = EXCLUDED.role, updated_at = NOW()
            """,
            (user_id.lower(), role),
        )


def list_users(limit: int = 100) -> list[tuple[str, str]]:
    ensure_schema()
    conn = _get_conn()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT user_id, role FROM hr_users ORDER BY user_id ASC LIMIT %s",
            (limit,),
        )
        rows = cur.fetchall()
    return [(row[0], row[1]) for row in rows]


def bootstrap_from_env() -> None:
    """Seed initial users from HR_BOOTSTRAP_USERS env var.

    Format:
      HR_BOOTSTRAP_USERS=hr_admin:admin,alice:manager,bob:employee
    """
    global _bootstrap_done
    if _bootstrap_done:
        return

    raw = os.environ.get("HR_BOOTSTRAP_USERS", "").strip()
    if not raw:
        _bootstrap_done = True
        return

    entries: dict[str, str] = {}
    for part in raw.split(","):
        token = part.strip()
        if not token or ":" not in token:
            continue
        user_id, role = token.split(":", 1)
        user_id = user_id.strip().lower()
        role = role.strip().lower()
        if not user_id or role not in _ALLOWED_ROLES:
            continue
        entries[user_id] = role

    if entries:
        seed_users(entries)

    _bootstrap_done = True
