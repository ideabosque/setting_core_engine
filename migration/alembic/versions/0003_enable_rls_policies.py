# -*- coding: utf-8 -*-
"""Enable Row-Level Security policies on all partition-keyed tables.

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-06 00:24:00.000000
"""
from __future__ import print_function

__author__ = "bibow"

import os
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None

# Read the table prefix from env (same resolution as env.py)
_PREFIX = os.environ.get("PG_TABLE_PREFIX", "sce_")

RLS_TABLES = [
    "settings",
    "theme_settings",
]


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    for table in RLS_TABLES:
        full_name = f"{_PREFIX}{table}"
        op.execute(f"ALTER TABLE {full_name} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {full_name} FORCE ROW LEVEL SECURITY")
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {full_name}")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {full_name} "
            f"USING (partition_key = current_setting('app.tenant_id', true))"
        )


def downgrade() -> None:
    for table in RLS_TABLES:
        full_name = f"{_PREFIX}{table}"
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {full_name}")
        op.execute(f"ALTER TABLE {full_name} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {full_name} DISABLE ROW LEVEL SECURITY")