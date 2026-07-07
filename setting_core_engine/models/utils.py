# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging


def _initialize_tables(logger: logging.Logger) -> None:
    """Initialize persistence tables for the active backend."""
    from ..handlers.config import Config

    if Config.DB_BACKEND == "postgresql":
        from .postgresql.utils import initialize_tables

        initialize_tables(logger, Config.db_session)
        return

    from .dynamodb.theme_setting import create_theme_setting_table
    from .dynamodb.setting import create_setting_table

    create_theme_setting_table(logger)
    create_setting_table(logger)
