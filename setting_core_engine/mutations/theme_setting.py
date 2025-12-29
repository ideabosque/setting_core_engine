# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

from graphene import Boolean, Field, Mutation, String

from silvaengine_utility import JSON

from ..models.theme_setting import delete_theme_setting, insert_update_theme_setting
from ..types.theme_setting import ThemeSettingType


class InsertUpdateThemeSetting(Mutation):
    theme_setting = Field(ThemeSettingType)

    class Arguments:
        theme_type = String(required=True)
        setting = JSON(required=True)
        updated_by = String(required=False)

    @staticmethod
    def mutate(
        root: Any, info: Any, **kwargs: Dict[str, Any]
    ) -> "InsertUpdateThemeSetting":
        try:
            theme_setting = insert_update_theme_setting(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return InsertUpdateThemeSetting(theme_setting=theme_setting)


class DeleteThemeSetting(Mutation):
    ok = Boolean()

    class Arguments:
        theme_uuid = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "DeleteThemeSetting":
        try:
            ok = delete_theme_setting(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteThemeSetting(ok=ok)
