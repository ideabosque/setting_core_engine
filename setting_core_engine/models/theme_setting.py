#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "jeffreyw"

import functools
import logging
import traceback
from typing import Any, Dict

import pendulum
from graphene import ResolveInfo
from pynamodb.attributes import (
    MapAttribute,
    UnicodeAttribute,
    UTCDateTimeAttribute,
)
from pynamodb.indexes import AllProjection, LocalSecondaryIndex
from tenacity import retry, stop_after_attempt, wait_exponential

from silvaengine_dynamodb_base import (
    BaseModel,
    delete_decorator,
    insert_update_decorator,
    monitor_decorator,
    resolve_list_decorator,
)
from silvaengine_utility import method_cache
from silvaengine_utility.serializer import Serializer

from ..handlers.config import Config
from ..types.theme_setting import ThemeSettingType, ThemeSettingListType

class ThemeTypeIndex(LocalSecondaryIndex):
 
    class Meta:
        billing_mode = "PAY_PER_REQUEST"
        # All attributes are projected
        projection = AllProjection()
        index_name = "theme_type-index"

    partition_key = UnicodeAttribute(hash_key=True)
    theme_type = UnicodeAttribute(range_key=True)

class ThemeSettingModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "sce-theme_settings"

    partition_key = UnicodeAttribute(hash_key=True)
    theme_uuid = UnicodeAttribute(range_key=True)
    
    theme_type = UnicodeAttribute()

    theme_title = UnicodeAttribute()
    theme_description = UnicodeAttribute()
    setting = MapAttribute()
    updated_by = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()
    theme_type_index = ThemeTypeIndex()  


def purge_cache():
    def actual_decorator(original_function):
        @functools.wraps(original_function)
        def wrapper_function(*args, **kwargs):
            try:
                # Execute original function first
                result = original_function(*args, **kwargs)

                # Then purge cache after successful operation
                from .cache import purge_entity_cascading_cache

                # Get entity keys from kwargs or entity parameter
                entity_keys = {}
                partition_key = args[0].context.get("partition_key") or kwargs.get(
                    "partition_key"
                )

                # Try to get from entity parameter first (for updates)
                entity = kwargs.get("entity")
                if entity:
                    entity_keys["theme_uuid"] = getattr(entity, "theme_uuid", None)

                # Fallback to kwargs (for creates/deletes)
                if not entity_keys.get("theme_uuid"):
                    entity_keys["theme_uuid"] = kwargs.get("theme_uuid")

                # Only purge if we have the required keys
                if entity_keys.get("theme_uuid") and partition_key:
                    purge_entity_cascading_cache(
                        args[0].context.get("logger"),
                        entity_type="theme_setting",
                        context_keys={"partition_key": partition_key},
                        entity_keys=entity_keys,
                        cascade_depth=3,
                    )

                return result
            except Exception as e:
                log = traceback.format_exc()
                args[0].context.get("logger").error(log)
                raise e

        return wrapper_function

    return actual_decorator


def create_theme_setting_table(logger: logging.Logger) -> bool:
    """Create the Theme Setting table if it doesn't exist."""
    if not ThemeSettingModel.exists():
        # Create with on-demand billing (PAY_PER_REQUEST)
        ThemeSettingModel.create_table(billing_mode="PAY_PER_REQUEST", wait=True)
        logger.info("The Theme Setting table has been created.")
    return True


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
@method_cache(
    ttl=Config.get_cache_ttl(),
    cache_name=Config.get_cache_name("models", "theme_setting"),
)
def get_theme_setting(partition_key: str, theme_uuid: str) -> ThemeSettingModel:
    return ThemeSettingModel.get(partition_key, theme_uuid)


def get_theme_setting_count(partition_key: str, theme_uuid: str) -> int:
    return ThemeSettingModel.count(partition_key, ThemeSettingModel.theme_uuid == theme_uuid)


def get_theme_setting_type(
    info: ResolveInfo, theme_setting: ThemeSettingModel
) -> ThemeSettingType:
    try:
        theme_setting = theme_setting.__dict__["attribute_values"]
    except Exception as e:
        log = traceback.format_exc()
        info.context.get("logger").exception(log)
        raise e
    return ThemeSettingType(**Serializer.json_normalize(theme_setting))


def resolve_theme_setting(info: ResolveInfo, **kwargs: Dict[str, Any]) -> ThemeSettingType | None:
    count = get_theme_setting_count(info.context["partition_key"], kwargs["theme_uuid"])
    if count == 0:
        return None

    return get_theme_setting_type(
        info, get_theme_setting(info.context["partition_key"], kwargs["theme_uuid"])
    )


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=["partition_key", "theme_uuid"],
    list_type_class=ThemeSettingListType,
    type_funct=get_theme_setting_type,
    scan_index_forward=False,
)
def resolve_theme_setting_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    partition_key = info.context["partition_key"]
    theme_type = kwargs.get("theme_type")
    args = []
    inquiry_funct = ThemeSettingModel.scan
    count_funct = ThemeSettingModel.count
    if partition_key:
        args = [partition_key, None]
        inquiry_funct = ThemeSettingModel.query

    if theme_type:
        args[1] = ThemeSettingModel.theme_type == theme_type
        inquiry_funct = ThemeSettingModel.theme_type_index.query
        count_funct = ThemeSettingModel.theme_type_index.count

    the_filters = None
    
    if the_filters is not None:
        args.append(the_filters)
    return inquiry_funct, count_funct, args


@insert_update_decorator(
    keys={
        "hash_key": "partition_key",
        "range_key": "theme_uuid",
    },
    model_funct=get_theme_setting,
    count_funct=get_theme_setting_count,
    type_funct=get_theme_setting_type,
)
@purge_cache()
def insert_update_theme_setting(info: ResolveInfo, **kwargs: Dict[str, Any]) -> None:
    partition_key = info.context["partition_key"]
    theme_uuid = kwargs.get("theme_uuid")
    if kwargs.get("entity") is None:
        cols = {
            "theme_type": kwargs.get("theme_type"),
            "theme_title": kwargs.get("theme_title"),
            "theme_description": kwargs.get("theme_description"),
            "setting": kwargs.get("setting", {}),
            "updated_by": kwargs["updated_by"],
            "created_at": pendulum.now("UTC"),
            "updated_at": pendulum.now("UTC"),
        }

        ThemeSettingModel(
            partition_key,
            theme_uuid,
            **cols,
        ).save()
        return

    theme_setting = kwargs.get("entity")
    actions = [
        ThemeSettingModel.updated_by.set(kwargs["updated_by"]),
        ThemeSettingModel.updated_at.set(pendulum.now("UTC")),
    ]

    field_map = {
        "theme_title": ThemeSettingModel.theme_title,
        "theme_description": ThemeSettingModel.theme_description,
        "setting": ThemeSettingModel.setting
    }

    for key, field in field_map.items():
        if key in kwargs:
            actions.append(field.set(kwargs[key]))

    theme_setting.update(actions=actions)
    return


@delete_decorator(
    keys={
        "hash_key": "partition_key",
        "range_key": "theme_uuid",
    },
    model_funct=get_theme_setting,
)
@purge_cache()
def delete_theme_setting(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:

    kwargs["entity"].delete()
    return True
