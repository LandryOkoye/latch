import json
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from enum import Enum

from latch_core import config
from latch_core.models import Loop, LoopEvent, LoopEventType, LoopStatus, WindowSource

_SCHEMA = """
CREATE TABLE IF NOT EXISTS loops (
    id TEXT PRIMARY KEY,
    parent_id TEXT REFERENCES loops(id),
    promise TEXT NOT NULL,
    source_quote TEXT NOT NULL,
    source_meeting_id TEXT,
    owner_name TEXT NOT NULL,
    owner_email TEXT NOT NULL,
    counterparty_org TEXT NOT NULL,
    due_at TEXT NOT NULL,
    window_source TEXT NOT NULL,
    closure_criterion TEXT NOT NULL,
    stakes TEXT NOT NULL,
    status TEXT NOT NULL,
    touch_count INTEGER NOT NULL DEFAULT 0,
    deferral_count INTEGER NOT NULL DEFAULT 0,
    channels_tried TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    loop_id TEXT NOT NULL REFERENCES loops(id),
    event_type TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    channel TEXT,
    detail TEXT NOT NULL DEFAULT '',
    evidence_span TEXT,
    message_id TEXT,
    reply_text TEXT
);

CREATE INDEX IF NOT EXISTS idx_loops_parent ON loops(parent_id);
CREATE INDEX IF NOT EXISTS idx_loops_status_due ON loops(status, due_at);
CREATE INDEX IF NOT EXISTS idx_events_loop ON events(loop_id);
CREATE INDEX IF NOT EXISTS idx_events_message_id ON events(message_id);
"""

_UPDATABLE_FIELDS = set(Loop.model_fields) - {"id", "events"}


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(config.DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=10000;")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(_SCHEMA)


def reset_db() -> None:
    """Delete all loops and events. Used by the demo seed script."""
    with _connect() as conn:
        conn.execute("DELETE FROM events")
        conn.execute("DELETE FROM loops")


def delete_events(loop_id: str) -> None:
    """Delete all events for a loop. Used by the demo seed script to replace the
    auto-recorded CREATED event with a backdated history."""
    with _connect() as conn:
        conn.execute("DELETE FROM events WHERE loop_id = ?", (loop_id,))


def _row_to_loop(row: sqlite3.Row, events: list[LoopEvent] | None = None) -> Loop:
    return Loop(
        id=row["id"],
        parent_id=row["parent_id"],
        promise=row["promise"],
        source_quote=row["source_quote"],
        source_meeting_id=row["source_meeting_id"],
        owner_name=row["owner_name"],
        owner_email=row["owner_email"],
        counterparty_org=row["counterparty_org"],
        due_at=datetime.fromisoformat(row["due_at"]),
        window_source=WindowSource(row["window_source"]),
        closure_criterion=row["closure_criterion"],
        stakes=row["stakes"],
        status=LoopStatus(row["status"]),
        touch_count=row["touch_count"],
        deferral_count=row["deferral_count"],
        channels_tried=json.loads(row["channels_tried"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        events=events or [],
    )


def _row_to_event(row: sqlite3.Row) -> LoopEvent:
    return LoopEvent(
        id=row["id"],
        loop_id=row["loop_id"],
        event_type=LoopEventType(row["event_type"]),
        occurred_at=datetime.fromisoformat(row["occurred_at"]),
        channel=row["channel"],
        detail=row["detail"],
        evidence_span=row["evidence_span"],
        message_id=row["message_id"],
        reply_text=row["reply_text"],
    )


def create_loop(loop: Loop) -> Loop:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO loops (
                id, parent_id, promise, source_quote, source_meeting_id,
                owner_name, owner_email, counterparty_org, due_at, window_source,
                closure_criterion, stakes, status, touch_count, deferral_count,
                channels_tried, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                loop.id, loop.parent_id, loop.promise, loop.source_quote, loop.source_meeting_id,
                loop.owner_name, loop.owner_email, loop.counterparty_org, loop.due_at.isoformat(),
                loop.window_source.value, loop.closure_criterion, loop.stakes, loop.status.value,
                loop.touch_count, loop.deferral_count, json.dumps(loop.channels_tried),
                loop.created_at.isoformat(),
            ),
        )
    record_event(loop.id, LoopEventType.CREATED, detail=f"loop created: {loop.promise!r}")
    return get_loop(loop.id)


def get_loop(loop_id: str) -> Loop | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM loops WHERE id = ?", (loop_id,)).fetchone()
        if row is None:
            return None
        events = [
            _row_to_event(r)
            for r in conn.execute(
                "SELECT * FROM events WHERE loop_id = ? ORDER BY occurred_at", (loop_id,)
            ).fetchall()
        ]
    return _row_to_loop(row, events)


def update_loop(loop_id: str, **fields) -> Loop | None:
    """Update one or more Loop columns. Enums/lists/datetimes are serialised automatically."""
    unknown = set(fields) - _UPDATABLE_FIELDS
    if unknown:
        raise ValueError(f"not updatable fields: {sorted(unknown)}")
    if not fields:
        return get_loop(loop_id)

    columns = []
    values: list[object] = []
    for key, value in fields.items():
        if key == "channels_tried":
            value = json.dumps(value)
        elif isinstance(value, Enum):
            value = value.value
        elif isinstance(value, datetime):
            value = value.isoformat()
        columns.append(f"{key} = ?")
        values.append(value)
    values.append(loop_id)

    with _connect() as conn:
        conn.execute(f"UPDATE loops SET {', '.join(columns)} WHERE id = ?", values)
    return get_loop(loop_id)


def list_loops(status: LoopStatus | None = None) -> list[Loop]:
    query = "SELECT * FROM loops"
    params: tuple = ()
    if status is not None:
        query += " WHERE status = ?"
        params = (status.value,)
    query += " ORDER BY due_at"
    with _connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_loop(r) for r in rows]


def meeting_ingested(meeting_id: str) -> bool:
    with _connect() as conn:
        row = conn.execute("SELECT 1 FROM loops WHERE source_meeting_id = ? LIMIT 1", (meeting_id,)).fetchone()
    return row is not None


def fetch_children(loop_id: str) -> list[Loop]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM loops WHERE parent_id = ? ORDER BY created_at", (loop_id,)
        ).fetchall()
    return [_row_to_loop(r) for r in rows]


def record_event(
    loop_id: str,
    event_type: LoopEventType,
    *,
    channel: str | None = None,
    detail: str = "",
    evidence_span: str | None = None,
    message_id: str | None = None,
    reply_text: str | None = None,
    occurred_at: datetime | None = None,
) -> LoopEvent:
    event = LoopEvent(
        id=str(uuid.uuid4()),
        loop_id=loop_id,
        event_type=event_type,
        occurred_at=occurred_at or datetime.now(),
        channel=channel,
        detail=detail,
        evidence_span=evidence_span,
        message_id=message_id,
        reply_text=reply_text,
    )
    with _connect() as conn:
        conn.execute(
            "INSERT INTO events (id, loop_id, event_type, occurred_at, channel, detail, evidence_span, message_id, reply_text) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                event.id, event.loop_id, event.event_type.value, event.occurred_at.isoformat(),
                event.channel, event.detail, event.evidence_span, event.message_id, event.reply_text,
            ),
        )
    return event


def find_event_by_message_id(message_id: str) -> LoopEvent | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM events WHERE message_id = ?", (message_id,)).fetchone()
    return _row_to_event(row) if row else None
