#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "jeffreyw"

from graphene import DateTime, List, ObjectType, String

from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSON


class SettingType(ObjectType):
    partition_key = String()
    setting_uuid = String()
    setting_type = String()
    setting = JSON()
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class SettingListType(ListObjectType):
    setting_list = List(SettingType)
