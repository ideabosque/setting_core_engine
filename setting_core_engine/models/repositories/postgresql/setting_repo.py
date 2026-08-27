# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict, Optional

import pendulum
from graphene import ResolveInfo

from ....handlers.config import Config
from ....types.setting import SettingListType, SettingType
from ...postgresql.setting import SettingModel
from ..base import EntityRepository
from ._base import _normalize, _get_partition_key, _purge_cache


def _new_id() -> str:
    import uuid

    return f"{uuid.uuid1().int % (10**20):020d}"


class SettingPGRepository(EntityRepository):
    @property
    def entity_type(self) -> str:
        return "setting"

    def get(self, **keys: Any) -> Optional[Dict[str, Any]]:
        partition_key = keys.get("partition_key")
        setting_uuid = keys.get("setting_uuid")
        if not partition_key or not setting_uuid:
            return None
        row = (
            Config.db_session.query(SettingModel)
            .filter(
                SettingModel.partition_key == partition_key,
                SettingModel.setting_uuid == setting_uuid,
            )
            .first()
        )
        return _normalize(row) if row else None

    def count(self, **keys: Any) -> int:
        partition_key = keys.get("partition_key")
        setting_uuid = keys.get("setting_uuid")
        if not partition_key or not setting_uuid:
            return 0
        return (
            Config.db_session.query(SettingModel)
            .filter(
                SettingModel.partition_key == partition_key,
                SettingModel.setting_uuid == setting_uuid,
            )
            .count()
        )

    def list(self, info: ResolveInfo, **filters: Any) -> Any:
        partition_key = _get_partition_key(info)
        page_number = filters.get("page_number") or 1
        limit = filters.get("limit") or 10
        setting_type = filters.get("setting_type")

        query = Config.db_session.query(SettingModel)
        if partition_key:
            query = query.filter(SettingModel.partition_key == partition_key)
        if setting_type:
            query = query.filter(SettingModel.setting_type == setting_type)

        total = query.count()
        rows = (
            query.order_by(SettingModel.updated_at.desc())
            .offset((page_number - 1) * limit)
            .limit(limit)
            .all()
        )
        return SettingListType(
            setting_list=[self.get_type(info, row) for row in rows],
            page_number=page_number,
            page_size=len(rows),
            total=total,
        )

    def insert_update(self, info: ResolveInfo, **kwargs: Any) -> Any:
        session = Config.db_session
        logger = info.context.get("logger")
        partition_key = kwargs.get("partition_key") or info.context.get("partition_key")
        setting_uuid = kwargs.get("setting_uuid") or _new_id()
        kwargs["setting_uuid"] = setting_uuid

        try:
            row = (
                session.query(SettingModel)
                .filter(
                    SettingModel.partition_key == partition_key,
                    SettingModel.setting_uuid == setting_uuid,
                )
                .first()
            )
            if row is None:
                row = SettingModel(
                    partition_key=partition_key,
                    setting_uuid=setting_uuid,
                    setting_type=kwargs.get("setting_type"),
                    setting=kwargs.get("setting", {}),
                    updated_by=kwargs.get("updated_by"),
                    created_at=pendulum.now("UTC"),
                    updated_at=pendulum.now("UTC"),
                )
                session.add(row)
            else:
                if "setting" in kwargs:
                    row.setting = kwargs["setting"]
                row.updated_by = kwargs.get("updated_by")
                row.updated_at = pendulum.now("UTC")

            session.commit()
            session.refresh(row)
            _purge_cache(
                info,
                entity_type="setting",
                entity_keys={"setting_uuid": setting_uuid},
                context_keys={"partition_key": partition_key},
            )
            return self.get_type(info, row)
        except Exception as e:
            session.rollback()
            if logger:
                logger.error(traceback.format_exc())
            raise e
        finally:
            Config.db_session.remove()

    def delete(self, info: ResolveInfo, **kwargs: Any) -> bool:
        session = Config.db_session
        logger = info.context.get("logger")
        partition_key = kwargs.get("partition_key") or info.context.get("partition_key")
        setting_uuid = kwargs.get("setting_uuid")

        try:
            row = (
                session.query(SettingModel)
                .filter(
                    SettingModel.partition_key == partition_key,
                    SettingModel.setting_uuid == setting_uuid,
                )
                .first()
            )
            if row is None:
                return True
            session.delete(row)
            session.commit()
            _purge_cache(
                info,
                entity_type="setting",
                entity_keys={"setting_uuid": setting_uuid},
                context_keys={"partition_key": partition_key},
            )
            return True
        except Exception as e:
            session.rollback()
            if logger:
                logger.error(traceback.format_exc())
            raise e
        finally:
            Config.db_session.remove()

    def resolve_single(self, info: ResolveInfo, **kwargs: Any) -> Optional[SettingType]:
        row = self.get(
            partition_key=info.context.get("partition_key"),
            setting_uuid=kwargs.get("setting_uuid"),
        )
        return SettingType(**row) if row else None

    def get_type(self, info: ResolveInfo, row: Any) -> Optional[SettingType]:
        data = _normalize(row)
        return SettingType(**data) if data else None
