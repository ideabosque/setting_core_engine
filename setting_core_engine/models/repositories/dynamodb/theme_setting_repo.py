# -*- coding: utf-8 -*-
from __future__ import print_function

from typing import Any, Dict, Optional

from ...dynamodb import theme_setting as _theme_setting_mod
from ..base import EntityRepository
from ._base import _normalize


class ThemeSettingRepository(EntityRepository):
    @property
    def entity_type(self) -> str:
        return "theme_setting"

    def get(self, **keys: Any) -> Optional[Dict[str, Any]]:
        partition_key = keys.get("partition_key")
        theme_uuid = keys.get("theme_uuid")
        if not partition_key or not theme_uuid:
            return None
        if _theme_setting_mod.get_theme_setting_count(partition_key, theme_uuid) == 0:
            return None
        return _normalize(_theme_setting_mod.get_theme_setting(partition_key, theme_uuid))

    def count(self, **keys: Any) -> int:
        partition_key = keys.get("partition_key")
        theme_uuid = keys.get("theme_uuid")
        if not partition_key or not theme_uuid:
            return 0
        return _theme_setting_mod.get_theme_setting_count(partition_key, theme_uuid)

    def list(self, info: Any, **filters: Any) -> Any:
        return _theme_setting_mod.resolve_theme_setting_list(info, **filters)

    def insert_update(self, info: Any, **kwargs: Any) -> Any:
        return _theme_setting_mod.insert_update_theme_setting(info, **kwargs)

    def delete(self, info: Any, **kwargs: Any) -> bool:
        return _theme_setting_mod.delete_theme_setting(info, **kwargs)

    def resolve_single(self, info: Any, **kwargs: Any) -> Any:
        return _theme_setting_mod.resolve_theme_setting(info, **kwargs)
