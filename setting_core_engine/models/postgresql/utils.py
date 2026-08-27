# -*- coding: utf-8 -*-
"""PostgreSQL table initialization and shared utilities.

Only imported when DB_BACKEND=postgresql.
"""
from __future__ import print_function

__author__ = "bibow"

import logging
from typing import Any

from .base import Base


def initialize_tables(logger: logging.Logger, db_session: Any, engine: Any = None) -> None:
    """Create all PostgreSQL tables that have been imported.

    This uses SQLAlchemy metadata.create_all() which is idempotent —
    it only creates tables that don't already exist.  After table creation,
    Row-Level Security (RLS) policies are applied to all partition-keyed
    tables to enforce tenant isolation.

    Parameters
    ----------
    logger : logging.Logger
        Logger instance for progress messages.
    db_session : Any
        SQLAlchemy scoped session (used to derive the engine when
        ``engine`` is not supplied).
    engine : Any, optional
        SQLAlchemy engine.  If ``None``, derived from ``db_session.get_bind()``.
    """
    # Import all model modules so their SQLAlchemy classes register
    # with the Base.metadata
    _import_all_models()

    if engine is None:
        engine = db_session.get_bind()

    Base.metadata.create_all(bind=engine, checkfirst=True)
    logger.info("PostgreSQL setting_core_engine tables initialized.")

    # Apply Row-Level Security policies on all partition-keyed tables.
    try:
        from ...utils.rls import create_rls_policies

        create_rls_policies(engine)
        logger.info("PostgreSQL RLS policies applied.")
    except Exception as e:
        logger.warning(f"RLS policy creation skipped: {e}")


def _import_all_models() -> None:
    """Import all PostgreSQL model modules to register them with Base.metadata."""
    model_modules = [
        ".setting",
        ".theme_setting",
    ]
    for mod_name in model_modules:
        try:
            __import__(
                f"setting_core_engine.models.postgresql{mod_name}",
                fromlist=["x"],
            )
        except ImportError:
            # Model not yet ported — skip silently
            _logger = logging.getLogger(__name__)
            _logger.debug(f"PostgreSQL model not yet available: {mod_name}")


__all__ = ["initialize_tables"]