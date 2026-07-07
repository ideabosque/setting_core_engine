# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

from graphene import Boolean, Field, Mutation, String
from silvaengine_utility import JSONCamelCase

from ..models.repositories import get_repo
from ..types.theme_setting import ThemeSettingType


class InsertUpdateThemeSetting(Mutation):
    theme_setting = Field(ThemeSettingType)

    class Arguments:
        theme_uuid = String(required=False)
        theme_type = String(required=True)
        theme_title = String(required=False)
        theme_description = String(required=False)
        setting = JSONCamelCase(required=True)
        updated_by = String(required=False)

    @staticmethod
    def mutate(
        root: Any, info: Any, **kwargs: Dict[str, Any]
    ) -> "InsertUpdateThemeSetting":
        try:
            theme_setting = get_repo("theme_setting").insert_update(info, **kwargs)
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
            ok = get_repo("theme_setting").delete(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteThemeSetting(ok=ok)
