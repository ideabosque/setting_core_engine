# -*- coding: utf-8 -*-
"""DynamoDB repositories wrapping the existing PynamoDB model modules."""
from __future__ import print_function

from typing import Dict

from ..base import EntityRepository


def register_all(registry: Dict[str, EntityRepository]) -> None:
    from .setting_repo import SettingRepository
    from .theme_setting_repo import ThemeSettingRepository

    for repo in [SettingRepository(), ThemeSettingRepository()]:
        registry[repo.entity_type] = repo


__all__ = ["register_all"]
