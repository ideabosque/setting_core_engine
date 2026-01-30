#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "jeffreyw"

from typing import Any, Dict

from graphene import ResolveInfo

from silvaengine_utility import method_cache

from ..handlers.config import Config

from ..models import theme_setting
from ..types.theme_setting import ThemeSettingListType, ThemeSettingType


def resolve_theme_setting(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> ThemeSettingType | None:
    return theme_setting.resolve_theme_setting(info, **kwargs)


@method_cache(ttl=Config.get_cache_ttl(), cache_name=Config.get_cache_name('queries', 'theme_setting'))
def resolve_theme_setting_list(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> ThemeSettingListType:
    return theme_setting.resolve_theme_setting_list(info, **kwargs)