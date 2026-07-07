#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, List, Optional

from graphene import Schema
from silvaengine_utility import Graphql, Serializer

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
                        {"action": "settingList", "label": "Setting List"},
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
            },
        }
    ]


class SettingCoreEngine(Graphql):
    def __init__(self, logger, **setting):
        Graphql.__init__(self, logger, **setting)

        # Backend initialization (DynamoDB Meta or PG session) is handled
        # by Config.initialize() based on the db_backend setting.
        Config.initialize(logger, **setting)

        self.logger = logger
        self.setting = setting

    def _apply_partition_defaults(self, params: Dict[str, Any]) -> None:
        """
        Ensure endpoint_id/part_id defaults and assemble partition_key.
        """
        endpoint_id = params.get("endpoint_id", self.setting.get("endpoint_id"))
        part_id = params.get("metadata", {}).get(
            "part_id", params.get("part_id", self.setting.get("part_id"))
        )

        if params.get("context") is None:
            params["context"] = {}

        if "endpoint_id" not in params["context"]:
            params["context"]["endpoint_id"] = endpoint_id
        if "part_id" not in params["context"]:
            params["context"]["part_id"] = part_id

        if "partition_key" not in params["context"]:
            if not endpoint_id or not part_id:
                self.logger.error(
                    f"Missing endpoint_id or part_id: endpoint_id={endpoint_id}, part_id={part_id}"
                )
                raise ValueError(
                    "Both 'endpoint_id' and 'part_id' are required to generate 'partition_key'."
                )
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


# ---------------------------------------------------------------------------
# Module-level dispatch wrappers for gateway integration
#
# These follow the same pattern as ai_agent_core_engine.main:dispatch_graphql:
# thin module-level functions that build an engine from the initialized Config
# singleton and delegate to the class methods.
#
# The SilvaEngine Gateway resolves these via importlib from routes.yaml:
#   dispatch: "setting_core_engine.main:dispatch_graphql"
# ---------------------------------------------------------------------------

# Cache the engine instance to avoid re-running Graphql.__init__ on every request.
_engine_instance: Optional["SettingCoreEngine"] = None


def _build_engine_from_config() -> "SettingCoreEngine":
    """Return a cached engine from the initialized Config singleton.

    The first call constructs the engine; subsequent calls return the
    same instance. ``Config.initialize()`` is already guarded by
    ``_initialized``, so the engine's settings never change after the
    first request.
    """
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = SettingCoreEngine(
            Config.logger, **Config.get_setting()
        )
    return _engine_instance


def _set_rls_context(partition_key: str) -> None:
    """Set RLS tenant context for PostgreSQL mode (no-op for DynamoDB)."""
    if Config.DB_BACKEND == "postgresql" and Config.db_session:
        from .utils.rls import set_rls_context

        session = Config.db_session()
        try:
            set_rls_context(session, partition_key)
        except Exception:
            session.rollback()
            raise


def _clear_rls_context() -> None:
    """Clear RLS session after request (PG only)."""
    if Config.DB_BACKEND == "postgresql" and Config.db_session:
        Config.db_session.remove()


def dispatch_graphql(**params: Any) -> Any:
    """Execute a GraphQL query using gateway-initialized settings.

    This is the HTTP GraphQL entry point, matching the pattern used by
    ai_agent_core_engine (``ai_agent_core_engine.main:dispatch_graphql``).

    In PostgreSQL mode, sets the RLS tenant context from partition_key
    before GraphQL execution and clears the session after.
    """
    engine = _build_engine_from_config()
    engine._apply_partition_defaults(params)
    partition_key = params.get("context", {}).get("partition_key")
    if partition_key:
        _set_rls_context(partition_key)
    try:
        return engine.setting_core_graphql(**params)
    finally:
        _clear_rls_context()