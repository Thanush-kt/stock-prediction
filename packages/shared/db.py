"""SQLAlchemy engine + session factory."""
from __future__ import annotations

from contextlib import contextmanager
import threading
from typing import Iterator, Sequence

from sqlalchemy import create_engine, insert as sa_insert, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session, sessionmaker

from packages.shared.config import get_settings

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine  # pylint: disable=global-statement
    if _engine is None:
        _engine = create_engine(get_settings().database_url, pool_pre_ping=True, future=True)
    return _engine


def get_sessionmaker() -> sessionmaker[Session]:
    global _SessionLocal  # pylint: disable=global-statement
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)
    return _SessionLocal


@contextmanager
def session_scope() -> Iterator[Session]:
    session = get_sessionmaker()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# Postgres' wire protocol caps bound parameters at 65535 per statement, and
# SQLite's SQLITE_MAX_VARIABLE_NUMBER is lower still on older builds. A single
# multi-row INSERT therefore has a row ceiling of (limit / columns) — which a
# multi-year indicator backfill exceeds. Chunk below the smaller limit.
MAX_BIND_PARAMS = 30_000


def upsert_ignore(
    session: Session,
    table,
    rows: Sequence[dict],
    index_elements: Sequence[str],
) -> int:
    """Insert rows, ignoring conflicts on `index_elements`. Works on Postgres + SQLite."""
    if not rows:
        return 0
    dialect = session.bind.dialect.name if session.bind else session.get_bind().dialect.name
    n_cols = max(len(rows[0]), 1)
    chunk_size = max(MAX_BIND_PARAMS // n_cols, 1)

    total = 0
    for start in range(0, len(rows), chunk_size):
        chunk = list(rows[start : start + chunk_size])
        if dialect == "postgresql":
            from sqlalchemy.dialects.postgresql import insert as pg_insert  # pylint: disable=import-outside-toplevel
            stmt = pg_insert(table).values(chunk).on_conflict_do_nothing(
                index_elements=list(index_elements)
            )
        elif dialect == "sqlite":
            from sqlalchemy.dialects.sqlite import insert as sqlite_insert  # pylint: disable=import-outside-toplevel
            stmt = sqlite_insert(table).values(chunk).on_conflict_do_nothing(
                index_elements=list(index_elements)
            )
        else:
            stmt = sa_insert(table).values(chunk).prefix_with("OR IGNORE")
        result = session.execute(stmt)
        # Drivers report -1 ("unknown") for some multi-row forms; clamp so the
        # caller never sees a negative insert count.
        total += max(result.rowcount or 0, 0)
    return total


def reset_engine_for_tests(url: str) -> None:
    """Rebind the engine + sessionmaker to a different URL (used by tests)."""
    global _engine, _SessionLocal  # pylint: disable=global-statement
    _engine = create_engine(url, pool_pre_ping=True, future=True)
    _SessionLocal = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)


RUN_SIGNALS_ADVISORY_LOCK_ID = 6004512906848782663  # 0x53544F434B534947 ('STOCKSIG')
_sqlite_thread_lock = threading.Lock()


@contextmanager
def run_signals_lock(bind: Engine | Connection | None = None) -> Iterator[bool]:
    """Acquire a run-signals execution lock.

    PostgreSQL:
        Uses a dedicated Engine connection to acquire a non-blocking session-level
        advisory lock via `pg_try_advisory_lock`. The lock is held on that dedicated
        connection for the duration of the context block and released on exit via
        `pg_advisory_unlock`. If PostgreSQL terminates the connection or the process
        dies, the advisory lock is automatically released by PostgreSQL.

    SQLite / Other:
        Uses an in-process `threading.Lock` to serialize threads within the same Python
        process. NOTE: This does NOT protect against separate OS processes; distributed
        cross-process locking requires PostgreSQL in production.

    Yields:
        bool: True if the lock was acquired, False otherwise.
    """
    engine: Engine
    if bind is None:
        engine = get_engine()
    elif isinstance(bind, Engine):
        engine = bind
    elif hasattr(bind, "engine") and isinstance(bind.engine, Engine):
        engine = bind.engine
    else:
        engine = get_engine()

    dialect = engine.dialect.name
    if dialect == "postgresql":
        with engine.connect() as conn:
            acquired = conn.execute(
                text("SELECT pg_try_advisory_lock(:lock_id)"),
                {"lock_id": RUN_SIGNALS_ADVISORY_LOCK_ID},
            ).scalar()
            if not acquired:
                yield False
                return
            try:
                yield True
            finally:
                try:
                    conn.execute(
                        text("SELECT pg_advisory_unlock(:lock_id)"),
                        {"lock_id": RUN_SIGNALS_ADVISORY_LOCK_ID},
                    )
                except Exception:  # pylint: disable=broad-exception-caught
                    pass
    else:
        acquired = _sqlite_thread_lock.acquire(blocking=False)
        if not acquired:
            yield False
            return
        try:
            yield True
        finally:
            _sqlite_thread_lock.release()
