"""
PostgreSQL client for storing scraped economic calendar events.

Configure with DATABASE_URL (preferred) or POSTGRES_URL, for example:
postgresql://user:password@host:5432/database
"""

import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor, execute_values
except ImportError:  # pragma: no cover - handled at runtime
    psycopg2 = None
    RealDictCursor = None
    execute_values = None


def is_postgres_available() -> bool:
    """Return True when PostgreSQL dependencies and connection URL are configured."""
    return bool(DATABASE_URL and psycopg2 is not None)


def get_connection():
    """Create a PostgreSQL connection."""
    if psycopg2 is None:
        raise RuntimeError("psycopg2 is not installed. Run: python3 -m pip install -r requirements.txt")
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL or POSTGRES_URL is not configured")
    return psycopg2.connect(DATABASE_URL)


def init_schema() -> None:
    """Create required PostgreSQL tables and indexes if they do not exist."""
    migration_path = Path(__file__).parent / "migrations" / "001_init_postgres.sql"
    migration_sql = migration_path.read_text()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(migration_sql)


def transform_scraped_data(raw_data: List[Dict], month: str, year: str) -> List[Dict]:
    """Transform structured scraper rows into records ready for PostgreSQL."""
    transformed_records = []

    for record in raw_data:
        clean_record = {
            "scraped_at": datetime.now().isoformat(),
            "source": record.get("source", "forex_factory"),
            "month": month,
            "year": int(year),
            "date": record.get("date", ""),
            "time": record.get("time", ""),
            "day": record.get("day", ""),
            "currency": record.get("currency", ""),
            "impact": record.get("impact", ""),
            "event": record.get("event", ""),
            "actual": record.get("actual", ""),
            "forecast": record.get("forecast", ""),
            "previous": record.get("previous", ""),
            "detail_url": record.get("detail", record.get("detail_url", "")),
            "event_key": f"{record.get('date', '')}-{record.get('time', '')}-{record.get('event', '')}",
            "is_high_impact": record.get("impact", "").lower() == "red",
            "has_data": bool(record.get("actual") or record.get("forecast") or record.get("previous")),
        }

        if clean_record["event"] and clean_record["date"]:
            transformed_records.append(clean_record)

    return transformed_records


def delete_events_by_month(month: str, year: str, source: str) -> Dict[str, Any]:
    """Delete events for a month/year/source before a replacement scrape."""
    if not is_postgres_available():
        return {"success": False, "error": "PostgreSQL not configured", "deleted_count": 0}

    try:
        init_schema()
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM economic_events WHERE month = %s AND year = %s AND source = %s",
                    (month, int(year), source),
                )
                deleted_count = cur.rowcount
        return {"success": True, "deleted_count": deleted_count, "month": month, "year": year, "source": source}
    except Exception as e:
        logger.error(f"Failed to delete PostgreSQL events: {e}")
        return {"success": False, "error": str(e), "deleted_count": 0}


def save_to_postgres(data: List[Dict], month: str, year: str, replace_existing: bool = False, source: str = "forex_factory") -> Dict[str, Any]:
    """Save structured economic events to PostgreSQL."""
    if not is_postgres_available():
        return {"success": False, "error": "PostgreSQL client not available. Check DATABASE_URL and requirements.", "saved_count": 0}

    try:
        init_schema()

        if replace_existing:
            delete_events_by_month(month, year, source)

        clean_data = transform_scraped_data(data, month, year)
        if not clean_data:
            return {"success": False, "error": "No valid data to save after transformation", "saved_count": 0}

        columns = [
            "scraped_at", "source", "month", "year", "date", "time", "day", "currency",
            "impact", "event", "actual", "forecast", "previous", "detail_url", "event_key",
            "is_high_impact", "has_data",
        ]
        values = [[record[column] for column in columns] for record in clean_data]

        with get_connection() as conn:
            with conn.cursor() as cur:
                execute_values(
                    cur,
                    f"""
                    INSERT INTO economic_events ({", ".join(columns)}) VALUES %s
                    ON CONFLICT (source, month, year, event_key) DO UPDATE SET
                        scraped_at = EXCLUDED.scraped_at,
                        date = EXCLUDED.date,
                        time = EXCLUDED.time,
                        day = EXCLUDED.day,
                        currency = EXCLUDED.currency,
                        impact = EXCLUDED.impact,
                        event = EXCLUDED.event,
                        actual = EXCLUDED.actual,
                        forecast = EXCLUDED.forecast,
                        previous = EXCLUDED.previous,
                        detail_url = EXCLUDED.detail_url,
                        is_high_impact = EXCLUDED.is_high_impact,
                        has_data = EXCLUDED.has_data,
                        updated_at = NOW()
                    """,
                    values,
                )
                saved_count = cur.rowcount

                cur.execute(
                    """
                    INSERT INTO scrape_sessions (scraped_at, source, month, year, total_events, saved_count)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (datetime.now().isoformat(), source, month, int(year), len(clean_data), saved_count),
                )

        return {"success": True, "saved_count": saved_count, "total_processed": len(clean_data), "month": month, "year": year, "source": source}
    except Exception as e:
        logger.error(f"Failed to save to PostgreSQL: {e}")
        return {"success": False, "error": str(e), "saved_count": 0}


def test_postgres_connection() -> Dict[str, Any]:
    """Test PostgreSQL connectivity and schema creation."""
    if not is_postgres_available():
        return {
            "connected": False,
            "error": "PostgreSQL not configured. Set DATABASE_URL/POSTGRES_URL and install requirements.",
            "url_configured": bool(DATABASE_URL),
            "driver_installed": psycopg2 is not None,
        }

    try:
        init_schema()
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT COUNT(*) AS event_count FROM economic_events")
                result = cur.fetchone()
        return {"connected": True, "event_count": result["event_count"]}
    except Exception as e:
        return {"connected": False, "error": str(e), "url_configured": bool(DATABASE_URL)}


def _parse_bool(value: Any) -> Optional[bool]:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _split_csv(value: Any) -> List[str]:
    if value in (None, ""):
        return []
    return [item.strip() for item in str(value).split(",") if item.strip()]


def _serialize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    serialized = dict(row)
    for key, value in serialized.items():
        if hasattr(value, "isoformat"):
            serialized[key] = value.isoformat()
    return serialized


def _build_event_where_clause(filters: Dict[str, Any]) -> tuple[List[str], List[Any]]:
    where_clauses = []
    params: List[Any] = []

    exact_fields = ["source", "month", "year", "impact", "currency", "date", "day"]
    for field in exact_fields:
        value = filters.get(field)
        if value not in (None, ""):
            values = _split_csv(value)
            if len(values) > 1:
                placeholders = ", ".join(["%s"] * len(values))
                where_clauses.append(f"{field} IN ({placeholders})")
                params.extend(int(item) if field == "year" else item for item in values)
            else:
                where_clauses.append(f"{field} = %s")
                params.append(int(value) if field == "year" else value)

    event_search = filters.get("event") or filters.get("q")
    if event_search not in (None, ""):
        where_clauses.append("event ILIKE %s")
        params.append(f"%{event_search}%")

    for field in ["is_high_impact", "has_data"]:
        parsed = _parse_bool(filters.get(field))
        if parsed is not None:
            where_clauses.append(f"{field} = %s")
            params.append(parsed)

    date_from = filters.get("date_from")
    if date_from not in (None, ""):
        where_clauses.append("to_date(date, 'DD/MM/YYYY') >= to_date(%s, 'DD/MM/YYYY')")
        params.append(date_from)

    date_to = filters.get("date_to")
    if date_to not in (None, ""):
        where_clauses.append("to_date(date, 'DD/MM/YYYY') <= to_date(%s, 'DD/MM/YYYY')")
        params.append(date_to)

    return where_clauses, params


def query_events(filters: Optional[Dict[str, Any]] = None, limit: int = 500, offset: int = 0) -> Dict[str, Any]:
    """Query events for API consumers with filters and pagination."""
    init_schema()
    filters = filters or {}
    limit = max(1, min(int(limit), 5000))
    offset = max(0, int(offset))

    where_clauses, params = _build_event_where_clause(filters)
    where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    order_by = filters.get("order_by", "date")
    order_map = {
        "date": "year, to_date(date, 'DD/MM/YYYY'), time, source, event",
        "scraped_at": "scraped_at DESC, source, event",
        "source": "source, year, to_date(date, 'DD/MM/YYYY'), time, event",
        "impact": "impact, year, to_date(date, 'DD/MM/YYYY'), time, event",
        "event": "event, year, to_date(date, 'DD/MM/YYYY'), time",
    }
    order_sql = order_map.get(order_by, order_map["date"])

    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(f"SELECT COUNT(*) AS total FROM economic_events{where_sql}", params)
            total = cur.fetchone()["total"]

            cur.execute(
                f"SELECT * FROM economic_events{where_sql} ORDER BY {order_sql} LIMIT %s OFFSET %s",
                params + [limit, offset],
            )
            rows = [_serialize_row(row) for row in cur.fetchall()]

    return {
        "events": rows,
        "count": len(rows),
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(rows) < total,
    }


def get_event_by_id(event_id: int) -> Optional[Dict[str, Any]]:
    """Fetch one event by database id."""
    init_schema()
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM economic_events WHERE id = %s", (event_id,))
            row = cur.fetchone()
            return _serialize_row(row) if row else None


def get_event_summary() -> Dict[str, Any]:
    """Return counts useful for API consumers/discovery."""
    init_schema()
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT source, COUNT(*) AS count FROM economic_events GROUP BY source ORDER BY source")
            by_source = [_serialize_row(row) for row in cur.fetchall()]

            cur.execute("SELECT impact, COUNT(*) AS count FROM economic_events GROUP BY impact ORDER BY impact")
            by_impact = [_serialize_row(row) for row in cur.fetchall()]

            cur.execute("SELECT month, year, COUNT(*) AS count FROM economic_events GROUP BY month, year ORDER BY year, month")
            by_month = [_serialize_row(row) for row in cur.fetchall()]

    return {"by_source": by_source, "by_impact": by_impact, "by_month": by_month}
