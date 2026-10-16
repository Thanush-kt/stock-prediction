"""PostgreSQL-specific advisory lock concurrency tests.

These tests verify the real PostgreSQL advisory locking behavior across separate
database connections and threads using an isolated test database. They run only
when a PostgreSQL instance is available and do NOT touch the application database
or modify existing records.
"""
from __future__ import annotations

import concurrent.futures
import os
import threading
import time
from urllib.parse import urlparse, urlunparse

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from packages.shared.config import get_settings
from packages.shared.db import RUN_SIGNALS_ADVISORY_LOCK_ID, run_signals_lock


def _is_postgres_available() -> bool:
    """Check if the configured PostgreSQL server is reachable."""
    settings = get_settings()
    url = settings.database_url
    if "postgresql" not in url:
        return False
    try:
        # Use postgres maintenance database to probe connectivity
        parsed = urlparse(url)
        probe_url = urlunparse(parsed._replace(path="/postgres"))
        probe_eng = create_engine(probe_url, poolclass=NullPool, connect_args={"connect_timeout": 3})
        with probe_eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        probe_eng.dispose()
        return True
    except Exception:  # pylint: disable=broad-exception-caught
        return False


pytestmark = pytest.mark.skipif(
    not _is_postgres_available(),
    reason="PostgreSQL is not available in the current environment",
)


@pytest.fixture(name="isolated_postgres_db")
def fixture_isolated_postgres_db():
    """Create a temporary, isolated database for testing advisory locks."""
    settings = get_settings()
    parsed = urlparse(settings.database_url)
    admin_url = urlunparse(parsed._replace(path="/postgres"))
    test_db_name = f"stockpred_lock_test_{os.getpid()}_{int(time.time())}"
    test_db_url = urlunparse(parsed._replace(path=f"/{test_db_name}"))

    admin_eng = create_engine(admin_url, isolation_level="AUTOCOMMIT", poolclass=NullPool)
    with admin_eng.connect() as conn:
        conn.execute(text(f"CREATE DATABASE {test_db_name}"))

    try:
        yield test_db_url
    finally:
        with admin_eng.connect() as conn:
            # Terminate any remaining connections before dropping
            conn.execute(
                text(
                    f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    f"WHERE datname = '{test_db_name}' AND pid <> pg_backend_pid()"
                )
            )
            conn.execute(text(f"DROP DATABASE IF EXISTS {test_db_name}"))
        admin_eng.dispose()


def test_postgres_advisory_lock_mutual_exclusion(isolated_postgres_db: str):
    """Verify:
    1. First execution acquires the lock.
    2. Second execution cannot acquire while the first holds it.
    3. Lock becomes available after first execution exits.
    """
    eng1 = create_engine(isolated_postgres_db, poolclass=NullPool)
    eng2 = create_engine(isolated_postgres_db, poolclass=NullPool)

    try:
        # Step 1: First execution acquires the advisory lock
        with run_signals_lock(eng1) as acquired1:
            assert acquired1 is True, "First execution should acquire the advisory lock"

            # Step 2: Second execution on separate connection cannot acquire while first holds it
            with run_signals_lock(eng2) as acquired2:
                assert acquired2 is False, "Second execution must be blocked while first holds lock"

        # Step 3: Lock becomes available after first execution exits
        with run_signals_lock(eng2) as acquired3:
            assert acquired3 is True, "Second execution should acquire lock after first exits"

    finally:
        eng1.dispose()
        eng2.dispose()


def test_postgres_advisory_lock_released_on_exception(isolated_postgres_db: str):
    """Verify that an exception in execution safely releases the advisory lock."""
    eng1 = create_engine(isolated_postgres_db, poolclass=NullPool)
    eng2 = create_engine(isolated_postgres_db, poolclass=NullPool)

    try:
        # First execution encounters an unhandled exception
        with pytest.raises(RuntimeError, match="simulated failure"):
            with run_signals_lock(eng1) as acquired1:
                assert acquired1 is True
                raise RuntimeError("simulated failure")

        # Second execution must immediately be able to acquire the lock
        with run_signals_lock(eng2) as acquired2:
            assert acquired2 is True, "Lock should be released despite previous exception"

    finally:
        eng1.dispose()
        eng2.dispose()


def test_postgres_advisory_lock_concurrent_threads(isolated_postgres_db: str):
    """Verify that concurrent threads using separate engines coordinate via PostgreSQL."""
    results: list[bool] = []
    lock_barrier = threading.Barrier(2)

    def worker():
        worker_eng = create_engine(isolated_postgres_db, poolclass=NullPool)
        try:
            lock_barrier.wait(timeout=5)
            with run_signals_lock(worker_eng) as acquired:
                if acquired:
                    time.sleep(0.1)  # Hold briefly to ensure contention
                return acquired
        finally:
            worker_eng.dispose()

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(worker)
        f2 = executor.submit(worker)
        r1 = f1.result()
        r2 = f2.result()

    results = [r1, r2]
    assert results.count(True) == 1, f"Exactly one worker must acquire the lock, got: {results}"
    assert results.count(False) == 1, f"Exactly one worker must be rejected, got: {results}"
