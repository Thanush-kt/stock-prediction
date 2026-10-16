"""Add partial unique index on orders(signal_id) where signal_id IS NOT NULL.

Revision ID: 0004_order_signal_unique
Revises: 0003_execution_tables
Create Date: 2026-10-10
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_order_signal_unique"
down_revision = "0003_execution_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Step 1: Detect whether duplicate signal_id records exist
    duplicate_query = sa.text(
        "SELECT signal_id, COUNT(*) AS cnt "
        "FROM orders "
        "WHERE signal_id IS NOT NULL "
        "GROUP BY signal_id "
        "HAVING COUNT(*) > 1"
    )

    try:
        dup_rows = conn.execute(duplicate_query).fetchall()
    except Exception:  # pylint: disable=broad-exception-caught
        # During offline SQL generation (alembic upgrade --sql), tables may not exist yet
        dup_rows = []

    if dup_rows:
        dup_signal_ids = [row[0] for row in dup_rows]
        details_query = sa.text(
            "SELECT o.id, o.symbol, o.signal_id, o.status, o.broker_order_id, "
            "COUNT(t.id) AS trade_count "
            "FROM orders o "
            "LEFT JOIN trades t ON t.order_id = o.id "
            "WHERE o.signal_id IN :dup_ids "
            "GROUP BY o.id, o.symbol, o.signal_id, o.status, o.broker_order_id"
        ).bindparams(sa.bindparam("dup_ids", expanding=True))

        details = conn.execute(details_query, {"dup_ids": dup_signal_ids}).fetchall()
        report_lines = [
            f"  Order ID={d[0]}, symbol={d[1]}, signal_id={d[2]}, status={d[3]}, "
            f"broker_order_id={d[4]}, associated_trades={d[5]}"
            for d in details
        ]
        report = "\n".join(report_lines)

        raise RuntimeError(
            "Migration 0004 halted: Found existing duplicate orders with the same signal_id. "
            "To prevent silent data corruption or loss of trade/broker records, manual resolution "
            "is required before applying uniqueness constraint.\n"
            f"Duplicate details:\n{report}"
        )

    # Step 2: Create partial unique index
    op.create_index(
        "uq_orders_signal_id",
        "orders",
        ["signal_id"],
        unique=True,
        postgresql_where=sa.text("signal_id IS NOT NULL"),
        sqlite_where=sa.text("signal_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_orders_signal_id",
        table_name="orders",
    )
