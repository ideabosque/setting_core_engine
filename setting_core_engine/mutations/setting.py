# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

from graphene import Boolean, Field, Mutation, String

from silvaengine_utility import JSONSnakeCase

from ..models.setting import delete_setting, insert_update_setting
from ..types.setting import SettingType


class InsertUpdateSetting(Mutation):
    setting = Field(SettingType)

    class Arguments:
        setting_type = String(required=True)
        setting = JSONSnakeCase(required=True)
        updated_by = String(required=False)

    @staticmethod
    def mutate(
        root: Any, info: Any, **kwargs: Dict[str, Any]
    ) -> "InsertUpdateSetting":
        try:
            setting = insert_update_setting(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return InsertUpdateSetting(setting=setting)


class DeleteSetting(Mutation):
    ok = Boolean()

    class Arguments:
        setting_uuid = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "DeleteSetting":
        try:
            ok = delete_setting(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteSetting(ok=ok)
