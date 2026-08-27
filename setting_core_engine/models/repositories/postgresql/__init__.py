# -*- coding: utf-8 -*-
"""PostgreSQL repositories for the PostgreSQL backend."""
from __future__ import print_function

from typing import Dict

from ..base import EntityRepository


def register_all(registry: Dict[str, EntityRepository]) -> None:
    from .setting_repo import SettingPGRepository
    from .theme_setting_repo import ThemeSettingPGRepository

    for repo in [SettingPGRepository(), ThemeSettingPGRepository()]:
        registry[repo.entity_type] = repo


__all__ = ["register_all"]
