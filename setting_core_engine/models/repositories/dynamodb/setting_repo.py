# -*- coding: utf-8 -*-
from __future__ import print_function

from typing import Any, Dict, Optional

from ...dynamodb import setting as _setting_mod
from ..base import EntityRepository
from ._base import _normalize


class SettingRepository(EntityRepository):
    @property
    def entity_type(self) -> str:
        return "setting"

    def get(self, **keys: Any) -> Optional[Dict[str, Any]]:
        partition_key = keys.get("partition_key")
        setting_uuid = keys.get("setting_uuid")
        if not partition_key or not setting_uuid:
            return None
        if _setting_mod.get_setting_count(partition_key, setting_uuid) == 0:
            return None
        return _normalize(_setting_mod.get_setting(partition_key, setting_uuid))

    def count(self, **keys: Any) -> int:
        partition_key = keys.get("partition_key")
        setting_uuid = keys.get("setting_uuid")
        if not partition_key or not setting_uuid:
            return 0
        return _setting_mod.get_setting_count(partition_key, setting_uuid)

    def list(self, info: Any, **filters: Any) -> Any:
        return _setting_mod.resolve_setting_list(info, **filters)

    def insert_update(self, info: Any, **kwargs: Any) -> Any:
        return _setting_mod.insert_update_setting(info, **kwargs)

    def delete(self, info: Any, **kwargs: Any) -> bool:
        return _setting_mod.delete_setting(info, **kwargs)

    def resolve_single(self, info: Any, **kwargs: Any) -> Any:
        return _setting_mod.resolve_setting(info, **kwargs)
