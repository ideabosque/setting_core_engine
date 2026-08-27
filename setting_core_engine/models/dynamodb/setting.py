#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

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

from ...handlers.config import Config
from ...types.setting import SettingType, SettingListType

class SettingTypeIndex(LocalSecondaryIndex):
 
    class Meta:
        billing_mode = "PAY_PER_REQUEST"
        # All attributes are projected
        projection = AllProjection()
        index_name = "setting_type-index"

    partition_key = UnicodeAttribute(hash_key=True)
    setting_type = UnicodeAttribute(range_key=True)

class SettingModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "sce-settings"

    partition_key = UnicodeAttribute(hash_key=True)
    setting_uuid = UnicodeAttribute(range_key=True)
    
    setting_type = UnicodeAttribute()
    setting = MapAttribute()
    updated_by = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()
    setting_type_index = SettingTypeIndex()  


def purge_cache():
    def actual_decorator(original_function):
        @functools.wraps(original_function)
        def wrapper_function(*args, **kwargs):
            try:
                # Execute original function first
                result = original_function(*args, **kwargs)

                # Then purge cache after successful operation
                from ..cache import purge_entity_cascading_cache

                # Get entity keys from kwargs or entity parameter
                entity_keys = {}
                partition_key = args[0].context.get("partition_key") or kwargs.get(
                    "partition_key"
                )

                # Try to get from entity parameter first (for updates)
                entity = kwargs.get("entity")
                if entity:
                    entity_keys["setting_uuid"] = getattr(entity, "setting_uuid", None)

                # Fallback to kwargs (for creates/deletes)
                if not entity_keys.get("setting_uuid"):
                    entity_keys["setting_uuid"] = kwargs.get("setting_uuid")

                # Only purge if we have the required keys
                if entity_keys.get("setting_uuid") and partition_key:
                    purge_entity_cascading_cache(
                        args[0].context.get("logger"),
                        entity_type="setting",
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


def create_setting_table(logger: logging.Logger) -> bool:
    """Create the Setting table if it doesn't exist."""
    if not SettingModel.exists():
        # Create with on-demand billing (PAY_PER_REQUEST)
        SettingModel.create_table(billing_mode="PAY_PER_REQUEST", wait=True)
        logger.info("The Setting table has been created.")
    return True


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
@method_cache(
    ttl=Config.get_cache_ttl(),
    cache_name=Config.get_cache_name("models", "setting"),
)
def get_setting(partition_key: str, setting_uuid: str) -> SettingModel:
    return SettingModel.get(partition_key, setting_uuid)


def get_setting_count(partition_key: str, setting_uuid: str) -> int:
    return SettingModel.count(partition_key, SettingModel.setting_uuid == setting_uuid)


def get_setting_type(
    info: ResolveInfo, setting: SettingModel
) -> SettingType:
    try:
        setting = setting.__dict__["attribute_values"]
    except Exception as e:
        log = traceback.format_exc()
        info.context.get("logger").exception(log)
        raise e
    return SettingType(**Serializer.json_normalize(setting))


def resolve_setting(info: ResolveInfo, **kwargs: Dict[str, Any]) -> SettingType | None:
    count = get_setting_count(info.context["partition_key"], kwargs["setting_uuid"])
    if count == 0:
        return None

    return get_setting_type(
        info, get_setting(info.context["partition_key"], kwargs["setting_uuid"])
    )


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=["partition_key", "setting_uuid"],
    list_type_class=SettingListType,
    type_funct=get_setting_type,
)
def resolve_setting_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    partition_key = info.context["partition_key"]
    setting_type = kwargs.get("setting_type")

    args = []
    inquiry_funct = SettingModel.scan
    count_funct = SettingModel.count
    if partition_key:
        args = [partition_key, None]
        inquiry_funct = SettingModel.query

    if setting_type:
        args[1] = SettingModel.setting_type == setting_type
        inquiry_funct = SettingModel.setting_type_index.query
        count_funct = SettingModel.setting_type_index.count

    the_filters = None
    
    if the_filters is not None:
        args.append(the_filters)

    return inquiry_funct, count_funct, args


@insert_update_decorator(
    keys={
        "hash_key": "partition_key",
        "range_key": "setting_uuid",
    },
    model_funct=get_setting,
    count_funct=get_setting_count,
    type_funct=get_setting_type,
)
@purge_cache()
def insert_update_setting(info: ResolveInfo, **kwargs: Dict[str, Any]) -> None:

    partition_key = info.context["partition_key"]
    setting_uuid = kwargs.get("setting_uuid")

    if kwargs.get("entity") is None:
        cols = {
            "setting_type": kwargs.get("setting_type"),
            "setting": kwargs.get("setting", {}),
            "updated_by": kwargs["updated_by"],
            "created_at": pendulum.now("UTC"),
            "updated_at": pendulum.now("UTC"),
        }

        SettingModel(
            partition_key,
            setting_uuid,
            **cols,
        ).save()
        return

    setting = kwargs.get("entity")
    actions = [
        SettingModel.updated_by.set(kwargs["updated_by"]),
        SettingModel.updated_at.set(pendulum.now("UTC")),
    ]

    field_map = {
        "setting": SettingModel.setting,
    }

    for key, field in field_map.items():
        if key in kwargs:
            actions.append(field.set(kwargs[key]))

    setting.update(actions=actions)
    return


@delete_decorator(
    keys={
        "hash_key": "partition_key",
        "range_key": "setting_uuid",
    },
    model_funct=get_setting,
)
@purge_cache()
def delete_setting(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:

    kwargs["entity"].delete()
    return True