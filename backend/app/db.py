from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .database import DATABASE_URL, SQLALCHEMY_AVAILABLE, engine, initialize_schema

if SQLALCHEMY_AVAILABLE:
    from sqlalchemy import inspect, text
else:  # pragma: no cover - the local stdlib path has no SQLAlchemy dependency.
    inspect = None
    text = None

DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "travelmind.db"


def _database_url() -> str:
    return DATABASE_URL


def _sqlite_path() -> str:
    raw = _database_url()
    if raw.startswith("sqlite:///"):
        return raw.replace("sqlite:///", "", 1)
    if raw.startswith("sqlite://"):
        return raw.replace("sqlite://", "", 1)
    if raw.startswith("postgresql") or raw.startswith("postgres"):
        raise RuntimeError("PostgreSQL persistence requires SQLAlchemy; refusing to fall back to SQLite")
    return raw


def get_connection() -> sqlite3.Connection:
    if not _database_url().startswith("sqlite"):
        raise RuntimeError("The SQLite connection helper cannot connect to a non-SQLite DATABASE_URL")
    path = _sqlite_path()
    db_dir = Path(path).parent
    db_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _read_one(statement: str, params: dict[str, Any]) -> dict[str, Any] | None:
    if SQLALCHEMY_AVAILABLE and engine is not None:
        with engine.connect() as connection:
            row = connection.execute(text(statement), params).mappings().first()
            return dict(row) if row else None
    conn = get_connection()
    try:
        row = conn.execute(statement, params).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def _read_all(statement: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    if SQLALCHEMY_AVAILABLE and engine is not None:
        with engine.connect() as connection:
            rows = connection.execute(text(statement), params or {}).mappings().all()
            return [dict(row) for row in rows]
    conn = get_connection()
    try:
        return [dict(row) for row in conn.execute(statement, params or {}).fetchall()]
    finally:
        conn.close()


def _write(statement: str, params: dict[str, Any]) -> int:
    if SQLALCHEMY_AVAILABLE and engine is not None:
        with engine.begin() as connection:
            result = connection.execute(text(statement), params)
            return result.rowcount
    conn = get_connection()
    try:
        cursor = conn.execute(statement, params)
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db() -> None:
    if SQLALCHEMY_AVAILABLE and engine is not None:
        if not DATABASE_URL.startswith("sqlite"):
            return
        initialize_schema()
        columns = {column["name"] for column in inspect(engine).get_columns("trips")}
        if "plan_results" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE trips ADD COLUMN plan_results TEXT DEFAULT '{}'"))
        return
    conn = get_connection()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'traveler',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS trips (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                origin TEXT,
                destination TEXT,
                departure_date TEXT,
                return_date TEXT,
                duration_days INTEGER,
                travelers INTEGER NOT NULL DEFAULT 1,
                budget REAL,
                currency TEXT NOT NULL DEFAULT 'USD',
                status TEXT NOT NULL DEFAULT 'draft',
                summary TEXT,
                preferences TEXT DEFAULT '{}',
                plan_results TEXT DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS itinerary_items (
                id TEXT PRIMARY KEY,
                trip_id TEXT NOT NULL,
                day INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                cost REAL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(trip_id) REFERENCES trips(id)
            );

            CREATE TABLE IF NOT EXISTS budget_snapshots (
                id TEXT PRIMARY KEY,
                trip_id TEXT NOT NULL,
                currency TEXT NOT NULL DEFAULT 'USD',
                total REAL NOT NULL DEFAULT 0,
                contingency REAL NOT NULL DEFAULT 0,
                FOREIGN KEY(trip_id) REFERENCES trips(id)
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                trip_id TEXT,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(trip_id) REFERENCES trips(id),
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS preferences (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS subscriptions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                tier TEXT NOT NULL DEFAULT 'free',
                status TEXT NOT NULL DEFAULT 'active',
                current_period_end TEXT,
                cancel_at_period_end INTEGER DEFAULT 0,
                stripe_customer_id TEXT,
                stripe_subscription_id TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS payments (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                trip_id TEXT,
                amount REAL NOT NULL,
                currency TEXT NOT NULL DEFAULT 'USD',
                status TEXT NOT NULL DEFAULT 'succeeded',
                provider TEXT NOT NULL DEFAULT 'stripe',
                provider_payment_id TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS notifications (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                trip_id TEXT,
                type TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'unread',
                sent_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS provider_search_records (
                id TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                query TEXT NOT NULL,
                status TEXT NOT NULL,
                response_data TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS agent_execution_logs (
                id TEXT PRIMARY KEY,
                trip_id TEXT,
                agent_name TEXT NOT NULL,
                status TEXT NOT NULL,
                duration_ms INTEGER DEFAULT 0,
                error TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        trip_columns = {row["name"] for row in conn.execute("PRAGMA table_info(trips)").fetchall()}
        if "plan_results" not in trip_columns:
            conn.execute("ALTER TABLE trips ADD COLUMN plan_results TEXT DEFAULT '{}' ")
        conn.commit()
    finally:
        conn.close()


def reset_db() -> None:
    if SQLALCHEMY_AVAILABLE and engine is not None:
        for table in (
            "agent_execution_logs",
            "provider_search_records",
            "notifications",
            "payments",
            "subscriptions",
            "preferences",
            "conversations",
            "budget_snapshots",
            "itinerary_items",
            "trips",
            "users",
        ):
            _write(f"DELETE FROM {table}", {})
        return
    conn = get_connection()
    try:
        conn.executescript(
            """
            DELETE FROM agent_execution_logs;
            DELETE FROM provider_search_records;
            DELETE FROM notifications;
            DELETE FROM payments;
            DELETE FROM subscriptions;
            DELETE FROM preferences;
            DELETE FROM conversations;
            DELETE FROM budget_snapshots;
            DELETE FROM itinerary_items;
            DELETE FROM trips;
            DELETE FROM users;
            """
        )
        conn.commit()
    finally:
        conn.close()


def get_user_by_email(email: str) -> dict[str, Any] | None:
    return _read_one("SELECT * FROM users WHERE email = :email", {"email": email.lower()})


def get_user_by_id(user_id: str) -> dict[str, Any] | None:
    return _read_one("SELECT * FROM users WHERE id = :id", {"id": user_id})


def create_user(email: str, password_hash: str, full_name: str, role: str = "traveler") -> dict[str, Any]:
    user_id = str(uuid.uuid4())
    _write(
        "INSERT INTO users (id, email, password_hash, full_name, role, created_at) VALUES (:id, :email, :password_hash, :full_name, :role, :created_at)",
        {"id": user_id, "email": email.lower(), "password_hash": password_hash, "full_name": full_name, "role": role, "created_at": _now_iso()},
    )
    # Default free tier subscription
    get_or_create_subscription(user_id, tier="free")
    return get_user_by_id(user_id)


def list_users() -> list[dict[str, Any]]:
    return _read_all("SELECT * FROM users ORDER BY created_at DESC")


def create_trip(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    trip_id = str(uuid.uuid4())
    _write(
        """INSERT INTO trips (
            id, user_id, origin, destination, departure_date, return_date, duration_days,
            travelers, budget, currency, status, summary, preferences, plan_results, created_at
        ) VALUES (
            :id, :user_id, :origin, :destination, :departure_date, :return_date, :duration_days,
            :travelers, :budget, :currency, :status, :summary, :preferences, :plan_results, :created_at
        )""",
        {
            "id": trip_id, "user_id": user_id, "origin": payload.get("origin"),
            "destination": payload.get("destination"), "departure_date": payload.get("departure_date"),
            "return_date": payload.get("return_date"), "duration_days": payload.get("duration_days"),
            "travelers": int(payload.get("travelers", 1) or 1), "budget": payload.get("budget"),
            "currency": payload.get("currency", "USD"), "status": payload.get("status", "draft"),
            "summary": payload.get("summary"), "preferences": json.dumps(payload.get("preferences", {})),
            "plan_results": json.dumps(payload.get("plan_results", {})), "created_at": _now_iso(),
        },
    )
    return get_trip(trip_id)


def get_trip(trip_id: str) -> dict[str, Any] | None:
    data = _read_one("SELECT * FROM trips WHERE id = :id", {"id": trip_id})
    if data is None:
        return None
    data["preferences"] = json.loads(data.get("preferences") or "{}")
    data["plan_results"] = json.loads(data.get("plan_results") or "{}")
    return data


def list_trips(user_id: str | None = None) -> list[dict[str, Any]]:
    rows = _read_all(
        "SELECT * FROM trips WHERE user_id = :user_id ORDER BY created_at DESC" if user_id else "SELECT * FROM trips ORDER BY created_at DESC",
        {"user_id": user_id} if user_id else {},
    )
    for data in rows:
        data["preferences"] = json.loads(data.get("preferences") or "{}")
        data["plan_results"] = json.loads(data.get("plan_results") or "{}")
    return rows


def update_trip(trip_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    if not updates:
        return get_trip(trip_id)
    allowed_fields = {
        "origin", "destination", "departure_date", "return_date", "duration_days",
        "travelers", "budget", "currency", "status", "summary", "preferences", "plan_results",
    }
    if set(updates) - allowed_fields:
        raise ValueError("unsupported trip fields")
    fields = []
    params: dict[str, Any] = {"id": trip_id}
    for key, value in updates.items():
        params[key] = json.dumps(value) if key in {"preferences", "plan_results"} else value
        fields.append(f"{key} = :{key}")
    _write(f"UPDATE trips SET {', '.join(fields)} WHERE id = :id", params)
    return get_trip(trip_id)


def delete_trip(trip_id: str) -> bool:
    _write("DELETE FROM conversations WHERE trip_id = :id", {"id": trip_id})
    _write("DELETE FROM budget_snapshots WHERE trip_id = :id", {"id": trip_id})
    _write("DELETE FROM itinerary_items WHERE trip_id = :id", {"id": trip_id})
    _write("DELETE FROM agent_execution_logs WHERE trip_id = :id", {"id": trip_id})
    return _write("DELETE FROM trips WHERE id = :id", {"id": trip_id}) > 0


def add_conversation_message(user_id: str, trip_id: str | None, role: str, content: str) -> dict[str, Any]:
    msg_id = str(uuid.uuid4())
    _write(
        "INSERT INTO conversations (id, trip_id, user_id, role, content, created_at) VALUES (:id, :trip_id, :user_id, :role, :content, :created_at)",
        {"id": msg_id, "trip_id": trip_id, "user_id": user_id, "role": role, "content": content, "created_at": _now_iso()},
    )
    return {"id": msg_id, "trip_id": trip_id, "user_id": user_id, "role": role, "content": content}


def list_conversations(user_id: str, trip_id: str | None = None) -> list[dict[str, Any]]:
    if trip_id:
        return _read_all(
            "SELECT * FROM conversations WHERE user_id = :user_id AND trip_id = :trip_id ORDER BY created_at ASC",
            {"user_id": user_id, "trip_id": trip_id},
        )
    return _read_all("SELECT * FROM conversations WHERE user_id = :user_id ORDER BY created_at ASC", {"user_id": user_id})


def set_preference(user_id: str, key: str, value: Any) -> dict[str, Any]:
    existing = _read_one("SELECT id FROM preferences WHERE user_id = :user_id AND key = :key", {"user_id": user_id, "key": key})
    if existing:
        _write("UPDATE preferences SET value = :value, created_at = :created_at WHERE id = :id", {
            "value": json.dumps(value), "created_at": _now_iso(), "id": existing["id"],
        })
    else:
        _write(
            "INSERT INTO preferences (id, user_id, key, value, created_at) VALUES (:id, :user_id, :key, :value, :created_at)",
            {"id": str(uuid.uuid4()), "user_id": user_id, "key": key, "value": json.dumps(value), "created_at": _now_iso()},
        )
    return {"user_id": user_id, "key": key, "value": value}


def get_preferences(user_id: str) -> dict[str, Any]:
    rows = _read_all("SELECT key, value FROM preferences WHERE user_id = :user_id ORDER BY created_at ASC", {"user_id": user_id})
    result: dict[str, Any] = {}
    for row in rows:
        try:
            result[row["key"]] = json.loads(row["value"])
        except json.JSONDecodeError:
            result[row["key"]] = row["value"]
    return result


# --- SaaS Subscriptions & Billing ---

TIER_LIMITS = {
    "free": {"trip_limit": 3, "ai_model": "standard", "features": ["basic_planning", "manual_export"]},
    "pro": {"trip_limit": 1000, "ai_model": "advanced_gemini", "features": ["live_amadeus", "unlimited_trips", "n8n_sync"]},
    "enterprise": {"trip_limit": 10000, "ai_model": "premium_multi_agent", "features": ["live_amadeus", "whatsapp_assistant", "custom_branding"]},
}


def get_or_create_subscription(user_id: str, tier: str = "free") -> dict[str, Any]:
    sub = _read_one("SELECT * FROM subscriptions WHERE user_id = :user_id", {"user_id": user_id})
    if sub:
        sub_dict = dict(sub)
        sub_dict["limits"] = TIER_LIMITS.get(sub_dict.get("tier", "free"), TIER_LIMITS["free"])
        return sub_dict

    sub_id = str(uuid.uuid4())
    _write(
        "INSERT INTO subscriptions (id, user_id, tier, status, created_at) VALUES (:id, :user_id, :tier, 'active', :created_at)",
        {"id": sub_id, "user_id": user_id, "tier": tier, "created_at": _now_iso()},
    )
    new_sub = _read_one("SELECT * FROM subscriptions WHERE id = :id", {"id": sub_id})
    res = dict(new_sub) if new_sub else {"id": sub_id, "user_id": user_id, "tier": tier, "status": "active"}
    res["limits"] = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
    return res


def update_subscription(user_id: str, tier: str, status: str = "active") -> dict[str, Any]:
    sub = get_or_create_subscription(user_id)
    _write(
        "UPDATE subscriptions SET tier = :tier, status = :status WHERE user_id = :user_id",
        {"tier": tier, "status": status, "user_id": user_id},
    )
    return get_or_create_subscription(user_id)


def check_user_trip_quota(user_id: str) -> dict[str, Any]:
    sub = get_or_create_subscription(user_id)
    tier = sub.get("tier", "free")
    limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
    max_trips = limits["trip_limit"]
    current_trips = len(list_trips(user_id))
    remaining = max(0, max_trips - current_trips)
    allowed = current_trips < max_trips
    return {
        "tier": tier,
        "current_trips": current_trips,
        "max_trips": max_trips,
        "remaining_trips": remaining,
        "allowed": allowed,
        "upgrade_required": not allowed,
    }


def create_payment(user_id: str, amount: float, currency: str = "USD", trip_id: str | None = None, provider_payment_id: str | None = None) -> dict[str, Any]:
    pay_id = str(uuid.uuid4())
    _write(
        "INSERT INTO payments (id, user_id, trip_id, amount, currency, status, provider_payment_id, created_at) VALUES (:id, :user_id, :trip_id, :amount, :currency, 'succeeded', :provider_payment_id, :created_at)",
        {"id": pay_id, "user_id": user_id, "trip_id": trip_id, "amount": amount, "currency": currency, "provider_payment_id": provider_payment_id, "created_at": _now_iso()},
    )
    return {"id": pay_id, "user_id": user_id, "amount": amount, "currency": currency, "status": "succeeded"}


def list_payments(user_id: str) -> list[dict[str, Any]]:
    return _read_all("SELECT * FROM payments WHERE user_id = :user_id ORDER BY created_at DESC", {"user_id": user_id})


# --- Notifications ---

def create_notification(user_id: str, type: str, title: str, message: str, trip_id: str | None = None) -> dict[str, Any]:
    notif_id = str(uuid.uuid4())
    _write(
        "INSERT INTO notifications (id, user_id, trip_id, type, title, message, status, created_at) VALUES (:id, :user_id, :trip_id, :type, :title, :message, 'unread', :created_at)",
        {"id": notif_id, "user_id": user_id, "trip_id": trip_id, "type": type, "title": title, "message": message, "created_at": _now_iso()},
    )
    return {"id": notif_id, "user_id": user_id, "type": type, "title": title, "message": message, "status": "unread"}


def list_notifications(user_id: str, limit: int = 20) -> list[dict[str, Any]]:
    return _read_all(
        "SELECT * FROM notifications WHERE user_id = :user_id ORDER BY created_at DESC LIMIT :limit",
        {"user_id": user_id, "limit": limit},
    )


def mark_notification_read(notification_id: str) -> bool:
    return _write("UPDATE notifications SET status = 'read' WHERE id = :id", {"id": notification_id}) > 0


# --- Admin Stats & Execution Logs ---

def log_provider_search(provider: str, query: str, status: str, response_data: Any = None) -> None:
    rec_id = str(uuid.uuid4())
    _write(
        "INSERT INTO provider_search_records (id, provider, query, status, response_data, created_at) VALUES (:id, :provider, :query, :status, :resp, :created_at)",
        {"id": rec_id, "provider": provider, "query": query, "status": status, "resp": json.dumps(response_data) if response_data else None, "created_at": _now_iso()},
    )


def log_agent_execution(trip_id: str | None, agent_name: str, status: str, duration_ms: int = 0, error: str = "") -> None:
    rec_id = str(uuid.uuid4())
    _write(
        "INSERT INTO agent_execution_logs (id, trip_id, agent_name, status, duration_ms, error, created_at) VALUES (:id, :trip_id, :agent_name, :status, :duration_ms, :error, :created_at)",
        {"id": rec_id, "trip_id": trip_id, "agent_name": agent_name, "status": status, "duration_ms": duration_ms, "error": error, "created_at": _now_iso()},
    )


def get_admin_stats() -> dict[str, Any]:
    total_users = _read_one("SELECT count(*) as count FROM users", {})
    total_trips = _read_one("SELECT count(*) as count FROM trips", {})
    sub_breakdown = _read_all("SELECT tier, count(*) as count FROM subscriptions GROUP BY tier", {})
    recent_users = _read_all("SELECT id, email, full_name, role, created_at FROM users ORDER BY created_at DESC LIMIT 5", {})
    recent_logs = _read_all("SELECT * FROM agent_execution_logs ORDER BY created_at DESC LIMIT 10", {})
    return {
        "total_users": total_users["count"] if total_users else 0,
        "total_trips": total_trips["count"] if total_trips else 0,
        "subscriptions": {row["tier"]: row["count"] for row in sub_breakdown},
        "recent_users": recent_users,
        "recent_logs": recent_logs,
        "system_status": "healthy",
        "database": "postgresql" if DATABASE_URL.startswith("postgres") else "sqlite",
    }


init_db()
