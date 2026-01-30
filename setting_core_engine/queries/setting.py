#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "jeffreyw"

from typing import Any, Dict

from graphene import ResolveInfo

from silvaengine_utility import method_cache

from ..handlers.config import Config

from ..models import setting
from ..types.setting import SettingListType, SettingType


def resolve_setting(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> SettingType | None:
    return setting.resolve_setting(info, **kwargs)


@method_cache(ttl=Config.get_cache_ttl(), cache_name=Config.get_cache_name('queries', 'setting'))
def resolve_setting_list(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> SettingListType:
    return setting.resolve_setting_list(info, **kwargs)