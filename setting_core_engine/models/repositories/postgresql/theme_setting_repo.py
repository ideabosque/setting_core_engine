# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict, Optional

import pendulum
from graphene import ResolveInfo

from ....handlers.config import Config
from ....types.theme_setting import ThemeSettingListType, ThemeSettingType
from ...postgresql.theme_setting import ThemeSettingModel
from ..base import EntityRepository
from ._base import _normalize, _get_partition_key, _purge_cache


def _new_id() -> str:
    import uuid

    return f"{uuid.uuid1().int % (10**20):020d}"


class ThemeSettingPGRepository(EntityRepository):
    @property
    def entity_type(self) -> str:
        return "theme_setting"

    def get(self, **keys: Any) -> Optional[Dict[str, Any]]:
        partition_key = keys.get("partition_key")
        theme_uuid = keys.get("theme_uuid")
        if not partition_key or not theme_uuid:
            return None
        row = (
            Config.db_session.query(ThemeSettingModel)
            .filter(
                ThemeSettingModel.partition_key == partition_key,
                ThemeSettingModel.theme_uuid == theme_uuid,
            )
            .first()
        )
        return _normalize(row) if row else None

    def count(self, **keys: Any) -> int:
        partition_key = keys.get("partition_key")
        theme_uuid = keys.get("theme_uuid")
        if not partition_key or not theme_uuid:
            return 0
        return (
            Config.db_session.query(ThemeSettingModel)
            .filter(
                ThemeSettingModel.partition_key == partition_key,
                ThemeSettingModel.theme_uuid == theme_uuid,
            )
            .count()
        )

    def list(self, info: ResolveInfo, **filters: Any) -> Any:
        partition_key = _get_partition_key(info)
        page_number = filters.get("page_number") or 1
        limit = filters.get("limit") or 10
        theme_type = filters.get("theme_type")

        query = Config.db_session.query(ThemeSettingModel)
        if partition_key:
            query = query.filter(ThemeSettingModel.partition_key == partition_key)
        if theme_type:
            query = query.filter(ThemeSettingModel.theme_type == theme_type)

        total = query.count()
        rows = (
            query.order_by(ThemeSettingModel.updated_at.desc())
            .offset((page_number - 1) * limit)
            .limit(limit)
            .all()
        )
        return ThemeSettingListType(
            theme_setting_list=[self.get_type(info, row) for row in rows],
            page_number=page_number,
            page_size=len(rows),
            total=total,
        )

    def insert_update(self, info: ResolveInfo, **kwargs: Any) -> Any:
        session = Config.db_session
        logger = info.context.get("logger")
        partition_key = kwargs.get("partition_key") or info.context.get("partition_key")
        theme_uuid = kwargs.get("theme_uuid") or _new_id()
        kwargs["theme_uuid"] = theme_uuid

        try:
            row = (
                session.query(ThemeSettingModel)
                .filter(
                    ThemeSettingModel.partition_key == partition_key,
                    ThemeSettingModel.theme_uuid == theme_uuid,
                )
                .first()
            )
            if row is None:
                row = ThemeSettingModel(
                    partition_key=partition_key,
                    theme_uuid=theme_uuid,
                    theme_type=kwargs.get("theme_type"),
                    theme_title=kwargs.get("theme_title"),
                    theme_description=kwargs.get("theme_description"),
                    setting=kwargs.get("setting", {}),
                    updated_by=kwargs.get("updated_by"),
                    created_at=pendulum.now("UTC"),
                    updated_at=pendulum.now("UTC"),
                )
                session.add(row)
            else:
                for field in ["theme_title", "theme_description", "setting"]:
                    if field in kwargs:
                        setattr(row, field, kwargs[field])
                row.updated_by = kwargs.get("updated_by")
                row.updated_at = pendulum.now("UTC")

            session.commit()
            session.refresh(row)
            _purge_cache(
                info,
                entity_type="theme_setting",
                entity_keys={"theme_uuid": theme_uuid},
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
        theme_uuid = kwargs.get("theme_uuid")

        try:
            row = (
                session.query(ThemeSettingModel)
                .filter(
                    ThemeSettingModel.partition_key == partition_key,
                    ThemeSettingModel.theme_uuid == theme_uuid,
                )
                .first()
            )
            if row is None:
                return True
            session.delete(row)
            session.commit()
            _purge_cache(
                info,
                entity_type="theme_setting",
                entity_keys={"theme_uuid": theme_uuid},
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

    def resolve_single(self, info: ResolveInfo, **kwargs: Any) -> Optional[ThemeSettingType]:
        row = self.get(
            partition_key=info.context.get("partition_key"),
            theme_uuid=kwargs.get("theme_uuid"),
        )
        return ThemeSettingType(**row) if row else None

    def get_type(self, info: ResolveInfo, row: Any) -> Optional[ThemeSettingType]:
        data = _normalize(row)
        return ThemeSettingType(**data) if data else None
