# -*- coding: utf-8 -*-
"""Create theme_settings table (partition-keyed, RLS)

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-06 00:16:00.000000
"""
from __future__ import print_function

__author__ = "bibow"

import os
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None

# Read the table prefix from env (same resolution as env.py)
_PREFIX = os.environ.get("PG_TABLE_PREFIX", "sce_")


def upgrade() -> None:
    op.create_table(
        f"{_PREFIX}theme_settings",
        sa.Column("partition_key", sa.String(128), primary_key=True),
        sa.Column("theme_uuid", sa.String(), primary_key=True),
        sa.Column("theme_type", sa.String(), nullable=False),
        sa.Column("theme_title", sa.String(), nullable=True),
        sa.Column("theme_description", sa.String(), nullable=True),
        sa.Column("setting", postgresql.JSONB, nullable=True),
        sa.Column("updated_by", sa.String(64), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index(
        f"{_PREFIX}ix_theme_settings_partition_theme_type",
        f"{_PREFIX}theme_settings",
        ["partition_key", "theme_type"],
    )


def downgrade() -> None:
    op.drop_index(
        f"{_PREFIX}ix_theme_settings_partition_theme_type",
        table_name=f"{_PREFIX}theme_settings",
    )
    op.drop_table(f"{_PREFIX}theme_settings")