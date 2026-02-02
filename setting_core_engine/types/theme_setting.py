#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "jeffreyw"

from graphene import DateTime, List, ObjectType, String

from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSONCamelCase


class ThemeSettingType(ObjectType):
    partition_key = String()
    theme_uuid = String()
    theme_type = String()
    theme_title = String()
    theme_description = String()
    setting = JSONCamelCase()
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class ThemeSettingListType(ListObjectType):
    theme_setting_list = List(ThemeSettingType)
