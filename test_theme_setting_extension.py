#!/usr/bin/env python3
import sys
sys.path.insert(0, "/Users/Garabateador/Workspace/abacusipllc/backend/gpt/setting_core_engine")
sys.path.insert(0, "/Users/Garabateador/Workspace/abacusipllc/backend/gpt/silvaengine_definitions")
sys.path.insert(0, "/Users/Garabateador/Workspace/abacusipllc/backend/gpt/silvaengine_constants")
sys.path.insert(0, "/Users/Garabateador/Workspace/abacusipllc/backend/gpt/silvaengine_utility")
sys.path.insert(0, "/Users/Garabateador/Workspace/abacusipllc/backend/gpt/silvaengine_dynamodb_base")

from setting_core_engine.types.theme_setting import ThemeSettingType, CoordinationBriefType, AgentBriefType
from setting_core_engine.schema import Query, Mutations, type_class
from graphene import Schema


def test_original_fields_preserved():
    original_fields = [
        "partition_key", "theme_uuid", "theme_type", "theme_title",
        "theme_description", "setting", "updated_by", "created_at", "updated_at",
    ]
    for f in original_fields:
        assert f in ThemeSettingType._meta.fields, f"Missing original field: {f}"
    print("✅ Test 1 passed: All original fields preserved")


def test_new_fields_present():
    assert "coordinations" in ThemeSettingType._meta.fields
    assert "agents" in ThemeSettingType._meta.fields
    print("✅ Test 2 passed: New fields (coordinations, agents) present")


def test_coordination_brief_type():
    coord_fields = list(CoordinationBriefType._meta.fields.keys())
    expected = [
        "partition_key", "coordination_uuid", "coordination_name",
        "coordination_description", "agents", "updated_by", "created_at", "updated_at",
    ]
    for f in expected:
        assert f in coord_fields, f"Missing coord field: {f}"
    print("✅ Test 3 passed: CoordinationBriefType fields correct")


def test_agent_brief_type():
    agent_fields = list(AgentBriefType._meta.fields.keys())
    expected = [
        "partition_key", "agent_uuid", "agent_name", "agent_description",
        "llm_provider", "llm_name", "status",
    ]
    for f in expected:
        assert f in agent_fields, f"Missing agent field: {f}"
    print("✅ Test 4 passed: AgentBriefType fields correct")


def test_resolve_methods_exist():
    assert hasattr(ThemeSettingType, "resolve_coordinations")
    assert hasattr(ThemeSettingType, "resolve_agents")
    print("✅ Test 5 passed: Resolve methods exist")


class MockInfo:
    context = {}


class MockParentEmpty:
    partition_key = None
    theme_uuid = None


class MockParentWithKey:
    partition_key = "gpt#nestaging"
    theme_uuid = "nonexistent-theme-uuid"


def test_resolve_coordinations_handles_missing_data():
    result = ThemeSettingType.resolve_coordinations(MockParentEmpty(), MockInfo())
    assert result == [], f"Expected empty list, got {result}"
    print("✅ Test 6 passed: resolve_coordinations handles missing data gracefully")


def test_resolve_agents_handles_missing_data():
    result = ThemeSettingType.resolve_agents(MockParentEmpty(), MockInfo())
    assert result == [], f"Expected empty list, got {result}"
    print("✅ Test 7 passed: resolve_agents handles missing data gracefully")


def test_resolve_coordinations_nonexistent_theme():
    result = ThemeSettingType.resolve_coordinations(MockParentWithKey(), MockInfo())
    assert result == [], f"Expected empty list for nonexistent theme, got {result}"
    print("✅ Test 8 passed: resolve_coordinations returns empty for nonexistent theme")


def test_schema_builds_successfully():
    schema = Schema(query=Query, mutation=Mutations, types=type_class())
    assert schema is not None
    print("✅ Test 9 passed: Schema builds successfully")


def test_schema_introspection():
    schema = Schema(query=Query, mutation=Mutations, types=type_class())
    introspection = schema.introspect()
    types_list = introspection["__schema"]["types"]
    type_names = [t["name"] for t in types_list]
    assert "ThemeSettingType" in type_names
    assert "CoordinationBriefType" in type_names
    assert "AgentBriefType" in type_names

    theme_type = [t for t in types_list if t["name"] == "ThemeSettingType"][0]
    field_names = [f["name"] for f in theme_type["fields"]]
    assert "coordinations" in field_names
    assert "agents" in field_names
    print("✅ Test 10 passed: Schema introspection confirms new fields")


def test_existing_queries_unchanged():
    schema = Schema(query=Query, mutation=Mutations, types=type_class())
    introspection = schema.introspect()
    query_type_info = introspection["__schema"]["queryType"]
    query_name = query_type_info["name"]
    assert query_name == "Query"
    all_types = introspection["__schema"]["types"]
    query_type_def = [t for t in all_types if t["name"] == "Query"][0]
    query_names = [f["name"] for f in query_type_def["fields"]]
    assert "themeSetting" in query_names
    assert "themeSettingList" in query_names
    assert "setting" in query_names
    assert "settingList" in query_names
    print("✅ Test 11 passed: All existing queries unchanged")


if __name__ == "__main__":
    test_original_fields_preserved()
    test_new_fields_present()
    test_coordination_brief_type()
    test_agent_brief_type()
    test_resolve_methods_exist()
    test_resolve_coordinations_handles_missing_data()
    test_resolve_agents_handles_missing_data()
    test_resolve_coordinations_nonexistent_theme()
    test_schema_builds_successfully()
    test_schema_introspection()
    test_existing_queries_unchanged()
    print("\n🎉 All 11 tests passed!")
