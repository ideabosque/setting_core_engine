# -*- coding: utf-8 -*-
"""Create settings table (partition-keyed, RLS)

Revision ID: 0001
Revises:
Create Date: 2026-07-06 00:08:00.000000
"""
from __future__ import print_function

__author__ = "bibow"

import os
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

# Read the table prefix from env (same resolution as env.py)
_PREFIX = os.environ.get("PG_TABLE_PREFIX", "sce_")


def upgrade() -> None:
    op.create_table(
        f"{_PREFIX}settings",
        sa.Column("partition_key", sa.String(128), primary_key=True),
        sa.Column("setting_uuid", sa.String(), primary_key=True),
        sa.Column("setting_type", sa.String(), nullable=False),
        sa.Column("setting", postgresql.JSONB, nullable=True),
        sa.Column("updated_by", sa.String(64), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index(
        f"{_PREFIX}ix_settings_partition_setting_type",
        f"{_PREFIX}settings",
        ["partition_key", "setting_type"],
    )


def downgrade() -> None:
    op.drop_index(
        f"{_PREFIX}ix_settings_partition_setting_type",
        table_name=f"{_PREFIX}settings",
    )
    op.drop_table(f"{_PREFIX}settings")