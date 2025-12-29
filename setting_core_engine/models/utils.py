# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
from typing import Any, Dict


def _initialize_tables(logger: logging.Logger) -> None:
    """Initialize all DynamoDB tables for the AI Coordination Engine."""
    from .theme_setting import create_theme_setting_table
    from .setting import create_setting_table

    create_theme_setting_table(logger)
    create_setting_table(logger)

