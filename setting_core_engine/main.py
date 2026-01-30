#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "jeffreyw"

from typing import Any, Dict, List
from graphene import Schema
from silvaengine_utility import Graphql, Serializer

from silvaengine_dynamodb_base import BaseModel

from .handlers.config import Config
from .schema import Mutations, Query, type_class
def deploy() -> list:
    return [
        {
            "service": "setting_core_engine",
            "class": "SettingCoreEngine",
            "functions": {
                "setting_core_graphql": {
                    "is_static": False,
                    "label": "Setting Core GraphQL",
                    "query": [
                        {"action": "ping", "label": "Ping"},
                        {"action": "themeSetting", "label": "Theme Setting"},
                        {"action": "themeSettingList", "label": "Theme Setting List"},
                        {"action": "setting", "label": "Setting"},
                        {"action": "settingList", "label": "Setting List"}
                    ],
                    "mutation": [
                        {
                            "action": "insertUpdateThemeSetting",
                            "label": "Insert Update Theme Setting",
                        },
                        {
                            "action": "DeleteThemeSetting",
                            "label": "Delete Theme Setting",
                        },
                        {
                            "action": "insertUpdateSetting",
                            "label": "Insert Update Setting",
                        },
                        {
                            "action": "DeleteSetting",
                            "label": "Delete Setting",
                        },
                    ],
                    "type": "RequestResponse",
                    "support_methods": ["POST"],
                    "is_auth_required": False,
                    "is_graphql": True,
                    "settings": "setting_core_engine",
                    "disabled_in_resources": True,  # Ignore adding to resource list.
                }
            }
        }
    ]

class SettingCoreEngine(Graphql):
    def __init__(self, logger, **setting):
        Graphql.__init__(self, logger, **setting)

        if (
            setting.get("region_name")
            and setting.get("aws_access_key_id")
            and setting.get("aws_secret_access_key")
        ):
            BaseModel.Meta.region = setting.get("region_name")
            BaseModel.Meta.aws_access_key_id = setting.get("aws_access_key_id")
            BaseModel.Meta.aws_secret_access_key = setting.get("aws_secret_access_key")

        Config.initialize(logger, **setting)

        self.logger = logger
        self.setting = setting
    
    def _apply_partition_defaults(self, params: Dict[str, Any]) -> None:
        """
        Ensure endpoint_id/part_id defaults and assemble partition_key.
        """
        ## Test the waters 🧪 before diving in!
        endpoint_id = params.get("endpoint_id", self.setting.get("endpoint_id"))
        part_id = params.get("custom_headers",{}).get("part_id", self.setting.get("part_id"))

        if params.get("context") is None:
            params["context"] = {}

        params["context"]["partition_key"] = f"{endpoint_id}#{part_id}"
    
    def setting_core_graphql(self, **params: Dict[str, Any]) -> Any:
        self._apply_partition_defaults(params)

        return self.execute(self.__class__.build_graphql_schema(), **params)

    @staticmethod
    def build_graphql_schema() -> Schema:
        return Schema(
            query=Query,
            mutation=Mutations,
            types=type_class()
        )


        


