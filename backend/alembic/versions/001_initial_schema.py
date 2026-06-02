"""Initial schema — таблица analysis_results

Revision ID: 001
Revises: None
Create Date: 2025-05-28
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "analysis_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("sentiment", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("processing_time_ms", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("analysis_results")
