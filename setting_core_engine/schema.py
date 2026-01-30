#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "jeffreyw"

import time
from typing import Any, Dict

from graphene import (
    Boolean,
    DateTime,
    Field,
    Int,
    List,
    ObjectType,
    ResolveInfo,
    String,
)

from .queries.theme_setting import resolve_theme_setting_list, resolve_theme_setting
from .mutations.theme_setting import InsertUpdateThemeSetting, DeleteThemeSetting
from .types.theme_setting import ThemeSettingListType, ThemeSettingType
from .queries.setting import resolve_setting_list, resolve_setting
from .mutations.setting import InsertUpdateSetting, DeleteSetting
from .types.setting import SettingType, SettingListType

def type_class():
    return [
        ThemeSettingType,
        ThemeSettingListType,
        SettingType,
        SettingListType
    ]


class Query(ObjectType):
    ping = String()
    theme_setting = Field(
        ThemeSettingType,
        theme_uuid=String(required=True)
    )

    theme_setting_list = Field(
        ThemeSettingListType,
        theme_type=String(required=False),
        page_number=Int(required=False),
        limit=Int(required=False)
    )

    setting = Field(
        SettingType,
        setting_uuid=String(required=True)
    )

    setting_list = Field(
        SettingListType,
        setting_type=String(required=False),
        page_number=Int(required=False),
        limit=Int(required=False)
    )

    def resolve_ping(self, info: ResolveInfo) -> str:
        return f"Hello at {time.strftime('%X')}!!"

    def resolve_theme_setting(self, info: ResolveInfo, **kwargs: Dict[str, Any]) -> ThemeSettingType:
        return resolve_theme_setting(info, **kwargs)
    
    def resolve_theme_setting_list(self, info: ResolveInfo, **kwargs: Dict[str, Any]) -> ThemeSettingListType:
        return resolve_theme_setting_list(info, **kwargs)
    
    def resolve_setting(self, info: ResolveInfo, **kwargs: Dict[str, Any]) -> SettingType:
        return resolve_setting(info, **kwargs)
    
    def resolve_setting_list(self, info: ResolveInfo, **kwargs: Dict[str, Any]) -> SettingListType:
        return resolve_setting_list(info, **kwargs)
    
class Mutations(ObjectType):
    insert_update_theme_setting = InsertUpdateThemeSetting.Field()
    delete_theme_setting = DeleteThemeSetting.Field()
    insert_update_setting = InsertUpdateSetting.Field()
    delete_setting = DeleteSetting.Field()
