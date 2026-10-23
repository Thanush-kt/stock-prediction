"""Add target_session, outcome tracking, and generated_at to predictions.

Revision ID: 0005_prediction_target_session
Revises: 0004_order_signal_unique
Create Date: 2026-10-16
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005_prediction_target_session"
down_revision = "0004_order_signal_unique"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("predictions", sa.Column("target_session", sa.Date(), nullable=True))
    op.add_column("predictions", sa.Column("data_cutoff_ts", sa.DateTime(timezone=True), nullable=True))
    op.add_column("predictions", sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.add_column("predictions", sa.Column("actual_close", sa.Float(), nullable=True))
    op.add_column("predictions", sa.Column("actual_label", sa.Integer(), nullable=True))
    op.add_column("predictions", sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_predictions_target_session", "predictions", ["target_session"])
    op.create_index("ix_predictions_evaluated_at", "predictions", ["evaluated_at"])


def downgrade() -> None:
    op.drop_index("ix_predictions_evaluated_at", table_name="predictions")
    op.drop_index("ix_predictions_target_session", table_name="predictions")
    op.drop_column("predictions", "evaluated_at")
    op.drop_column("predictions", "actual_label")
    op.drop_column("predictions", "actual_close")
    op.drop_column("predictions", "generated_at")
    op.drop_column("predictions", "data_cutoff_ts")
    op.drop_column("predictions", "target_session")
