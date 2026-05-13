#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "jeffreyw"

import logging
import traceback

from graphene import DateTime, Field, List, ObjectType, String
from promise import Promise

from silvaengine_definitions import AgentLoader, CoordinationModel
from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSONCamelCase, Serializer


class CoordinationBriefType(ObjectType):
    partition_key = String()
    coordination_uuid = String()
    coordination_name = String()
    coordination_description = String()
    agents = List(JSONCamelCase)
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class AgentBriefType(ObjectType):
    partition_key = String()
    agent_uuid = String()
    agent_name = String()
    agent_description = String()
    llm_provider = String()
    llm_name = String()
    status = String()


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
    coordinations = List(lambda: CoordinationBriefType)
    agents = List(lambda: AgentBriefType)

    @staticmethod
    def resolve_coordinations(parent, info):
        existing = getattr(parent, "_coordinations_data", None)
        if existing is not None:
            return existing

        partition_key = getattr(parent, "partition_key", None)
        theme_uuid = getattr(parent, "theme_uuid", None)
        if not partition_key or not theme_uuid:
            return []

        try:
            results = CoordinationModel.scan(
                filter_condition=(
                    (CoordinationModel.partition_key == partition_key)
                    & (CoordinationModel.theme_uuid == theme_uuid)
                )
            )
            coordinations = []
            for coordination in results:
                try:
                    data = coordination.__dict__.get("attribute_values", {})
                    normalized = Serializer.json_normalize(data)
                    coordinations.append(CoordinationBriefType(**normalized))
                except Exception:
                    continue
            return coordinations
        except Exception as e:
            logger = info.context.get("logger") if info.context else None
            if logger:
                logger.error(traceback.format_exc())
            return []

    @staticmethod
    def resolve_agents(parent, info):
        existing = getattr(parent, "_agents_data", None)
        if existing is not None:
            return existing

        partition_key = getattr(parent, "partition_key", None)
        if not partition_key:
            return []

        try:
            coordinations = ThemeSettingType.resolve_coordinations(parent, info)
            agent_uuids = set()
            for coordination in coordinations:
                agents_list = getattr(coordination, "agents", None) or []
                for agent_entry in agents_list:
                    if isinstance(agent_entry, dict) and agent_entry.get("agent_uuid"):
                        agent_uuids.add(agent_entry["agent_uuid"])

            if not agent_uuids:
                return []

            loader = AgentLoader(info=info)
            promises = []
            for agent_uuid in agent_uuids:
                promises.append(
                    loader.load((partition_key, agent_uuid))
                )

            return Promise.all(promises).then(
                lambda results: [
                    AgentBriefType(
                        partition_key=r.get("partition_key", ""),
                        agent_uuid=r.get("agent_uuid", ""),
                        agent_name=r.get("agent_name", ""),
                        agent_description=r.get("agent_description", ""),
                        llm_provider=r.get("llm_provider", ""),
                        llm_name=r.get("llm_name", ""),
                        status=r.get("status", ""),
                    )
                    for r in results
                    if r is not None
                ]
            )
        except Exception as e:
            logger = info.context.get("logger") if info.context else None
            if logger:
                logger.error(traceback.format_exc())
            return []


class ThemeSettingListType(ListObjectType):
    theme_setting_list = List(ThemeSettingType)
