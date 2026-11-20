"""M1 schema tests: constraints, migration up/down on a scratch DB, model <-> row mapping.

The migration is plain SQL kept portable (TEXT/INTEGER/CHECK) so it runs on stdlib sqlite3 here.
Run it on the real primary DB engine in staging before merge (see IMPL-PLAN M1 human check).
"""
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from app.digest.models import (
    SEND_COLUMNS,
    SEND_STATUSES,
    SUBSCRIPTION_COLUMNS,
    DigestSend,
    DigestSubscription,
)

MIGRATIONS = Path(__file__).resolve().parents[2] / "app" / "migrations"
NEW_TABLES = {"digest_subscription", "digest_send"}


def _migration_file() -> Path:
    files = sorted(MIGRATIONS.glob("*_create_digest_tables.sql"))
    assert len(files) == 1, files
    return files[0]


def _section(name: str) -> str:
    text = _migration_file().read_text()
    up_marker, down_marker = "-- migrate:up", "-- migrate:down"
    assert up_marker in text and down_marker in text
    up, down = text.split(up_marker, 1)[1].split(down_marker, 1)
    return {"up": up, "down": down}[name]


def _tables(conn) -> set:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    return {r[0] for r in rows}


def _objects(conn) -> set:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'")
    return {r[0] for r in rows}


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("PRAGMA foreign_keys = ON")
    c.executescript(_section("up"))
    yield c
    c.close()


NOW = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)


def _sub(**kw) -> DigestSubscription:
    base = dict(
        id="sub-1", user_id="u1", dashboard_id="d1", enabled=True, weekday=0, hour_local=9,
        tz="America/New_York", next_send_at=NOW, created_at=NOW, updated_at=NOW,
    )
    base.update(kw)
    return DigestSubscription(**base)


def _insert_sub(conn, sub: DigestSubscription):
    cols = ",".join(SUBSCRIPTION_COLUMNS)
    marks = ",".join("?" * len(SUBSCRIPTION_COLUMNS))
    conn.execute(f"INSERT INTO digest_subscription ({cols}) VALUES ({marks})", sub.as_row())


def _send(**kw) -> DigestSend:
    base = dict(id="send-1", subscription_id="sub-1", period_start=date(2026, 11, 16),
                status="sent", created_at=NOW)
    base.update(kw)
    return DigestSend(**base)


def _insert_send(conn, send: DigestSend):
    cols = ",".join(SEND_COLUMNS)
    marks = ",".join("?" * len(SEND_COLUMNS))
    conn.execute(f"INSERT INTO digest_send ({cols}) VALUES ({marks})", send.as_row())


# ---- migration up / down -------------------------------------------------------------

def test_up_creates_exactly_two_new_tables():
    c = sqlite3.connect(":memory:")
    before = _tables(c)
    c.executescript(_section("up"))
    assert _tables(c) - before == NEW_TABLES
    assert before == set()


def test_up_does_not_touch_existing_tables():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE users (id TEXT PRIMARY KEY, email TEXT)")
    c.execute("INSERT INTO users VALUES ('u1', 'x')")
    schema_before = c.execute("SELECT sql FROM sqlite_master WHERE name='users'").fetchone()
    c.executescript(_section("up"))
    assert c.execute("SELECT sql FROM sqlite_master WHERE name='users'").fetchone() == schema_before
    assert c.execute("SELECT * FROM users").fetchall() == [("u1", "x")]


def test_down_removes_everything_up_created():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE users (id TEXT PRIMARY KEY)")
    baseline = _objects(c)
    c.executescript(_section("up"))
    assert _objects(c) != baseline
    c.executescript(_section("down"))
    assert _objects(c) == baseline


def test_down_then_up_again_works():
    c = sqlite3.connect(":memory:")
    c.executescript(_section("up"))
    c.executescript(_section("down"))
    c.executescript(_section("up"))
    assert _tables(c) == NEW_TABLES


def test_migration_is_additive_only():
    import re
    up = re.sub(r"--[^\n]*", "", _section("up")).upper()
    statements = [s.strip() for s in up.split(";") if s.strip()]
    assert statements
    for stmt in statements:
        assert re.match(r"CREATE (TABLE|INDEX) ", stmt), stmt
    assert "DROP TABLE" in _section("down").upper()


# ---- subscription constraints --------------------------------------------------------

def test_subscription_roundtrip(conn):
    sub = _sub(last_sent_at=NOW, unsubscribed_at=None, consecutive_failures=2)
    _insert_sub(conn, sub)
    row = conn.execute(f"SELECT {','.join(SUBSCRIPTION_COLUMNS)} FROM digest_subscription").fetchone()
    assert DigestSubscription.from_row(row) == sub


def test_unique_user_and_dashboard(conn):
    _insert_sub(conn, _sub(id="a"))
    with pytest.raises(sqlite3.IntegrityError):
        _insert_sub(conn, _sub(id="b"))
    _insert_sub(conn, _sub(id="c", dashboard_id="d2"))
    _insert_sub(conn, _sub(id="d", user_id="u2"))


def test_primary_key_unique(conn):
    _insert_sub(conn, _sub(id="a"))
    with pytest.raises(sqlite3.IntegrityError):
        _insert_sub(conn, _sub(id="a", user_id="u2"))


@pytest.mark.parametrize("col,value", [
    ("weekday", -1), ("weekday", 7), ("hour_local", -1), ("hour_local", 24),
    ("enabled", 2), ("consecutive_failures", -1),
])
def test_subscription_check_constraints(conn, col, value):
    _insert_sub(conn, _sub(id="ok"))
    row = list(_sub(id="bad", user_id="u9").as_row())
    row[SUBSCRIPTION_COLUMNS.index(col)] = value
    marks = ",".join("?" * len(SUBSCRIPTION_COLUMNS))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(f"INSERT INTO digest_subscription ({','.join(SUBSCRIPTION_COLUMNS)}) VALUES ({marks})", row)


@pytest.mark.parametrize("col", ["user_id", "dashboard_id", "tz", "next_send_at", "created_at", "updated_at"])
def test_subscription_required_columns(conn, col):
    row = list(_sub(id="bad").as_row())
    row[SUBSCRIPTION_COLUMNS.index(col)] = None
    marks = ",".join("?" * len(SUBSCRIPTION_COLUMNS))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(f"INSERT INTO digest_subscription ({','.join(SUBSCRIPTION_COLUMNS)}) VALUES ({marks})", row)


def test_due_query_uses_index(conn):
    plan = conn.execute(
        "EXPLAIN QUERY PLAN SELECT id FROM digest_subscription WHERE enabled = 1 AND next_send_at <= ?",
        ("2026-11-20T12:00:00+00:00",),
    ).fetchall()
    assert any("USING" in r[3] and "INDEX" in r[3] and "SEARCH" in r[3] for r in plan), plan


# ---- send constraints ----------------------------------------------------------------

def test_send_roundtrip(conn):
    _insert_sub(conn, _sub())
    send = _send(provider_message_id="pm-1", summary_hash="abc123")
    _insert_send(conn, send)
    row = conn.execute(f"SELECT {','.join(SEND_COLUMNS)} FROM digest_send").fetchone()
    assert DigestSend.from_row(row) == send


def test_unique_subscription_and_period_is_the_double_send_guard(conn):
    _insert_sub(conn, _sub())
    _insert_send(conn, _send(id="s1"))
    with pytest.raises(sqlite3.IntegrityError):
        _insert_send(conn, _send(id="s2"))
    _insert_send(conn, _send(id="s3", period_start=date(2026, 11, 23)))


def test_send_requires_existing_subscription(conn):
    with pytest.raises(sqlite3.IntegrityError):
        _insert_send(conn, _send(subscription_id="missing"))


@pytest.mark.parametrize("status", sorted(SEND_STATUSES))
def test_send_accepts_each_documented_status(conn, status):
    _insert_sub(conn, _sub())
    _insert_send(conn, _send(status=status))


def test_send_rejects_unknown_status_in_db(conn):
    _insert_sub(conn, _sub())
    row = list(_send().as_row())
    row[SEND_COLUMNS.index("status")] = "sending"
    marks = ",".join("?" * len(SEND_COLUMNS))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(f"INSERT INTO digest_send ({','.join(SEND_COLUMNS)}) VALUES ({marks})", row)


def test_status_set_matches_eng_plan():
    assert SEND_STATUSES == {"sent", "skipped_empty", "skipped_no_access", "failed"}


def test_send_table_has_no_place_for_values_or_bodies(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(digest_send)")}
    assert cols == set(SEND_COLUMNS)
    assert not cols & {"body", "html", "email", "recipient", "values"}
    sub_cols = {r[1] for r in conn.execute("PRAGMA table_info(digest_subscription)")}
    assert not sub_cols & {"email", "recipient"}


def test_deleting_subscription_removes_its_sends(conn):
    _insert_sub(conn, _sub())
    _insert_send(conn, _send())
    conn.execute("DELETE FROM digest_subscription WHERE id = 'sub-1'")
    assert conn.execute("SELECT COUNT(*) FROM digest_send").fetchone()[0] == 0


# ---- model validation ----------------------------------------------------------------

@pytest.mark.parametrize("kw", [
    dict(weekday=7), dict(weekday=-1), dict(hour_local=24), dict(hour_local=-1),
    dict(consecutive_failures=-1), dict(user_id=""), dict(dashboard_id=""),
    dict(next_send_at=datetime(2026, 11, 20, 12, 0)),  # naive datetime: UTC must be explicit
])
def test_subscription_model_rejects_invalid(kw):
    with pytest.raises(ValueError):
        _sub(**kw)


def test_subscription_model_normalizes_to_utc_on_write():
    from datetime import timedelta
    plus5 = timezone(timedelta(hours=5))
    sub = _sub(next_send_at=datetime(2026, 11, 20, 17, 0, tzinfo=plus5))
    assert sub.as_row()[SUBSCRIPTION_COLUMNS.index("next_send_at")] == "2026-11-20T12:00:00+00:00"


def test_send_model_rejects_unknown_status():
    with pytest.raises(ValueError):
        _send(status="queued")


def test_columns_match_eng_plan():
    assert SUBSCRIPTION_COLUMNS == (
        "id", "user_id", "dashboard_id", "enabled", "weekday", "hour_local", "tz", "next_send_at",
        "last_sent_at", "consecutive_failures", "unsubscribed_at", "created_at", "updated_at",
    )
    assert SEND_COLUMNS == (
        "id", "subscription_id", "period_start", "status", "provider_message_id", "error_code",
        "summary_hash", "created_at",
    )
