# Continuous Integration Scenarios SOP — Setting Core Engine

## 1. Document Control

| Field | Value |
|---|---|
| SOP title | Setting Core Engine Live Integration SOP — In-Process GraphQL Engine Invocation |
| Version | 1.0.0 |
| Owner / contact | `bibow` |
| Last updated | 2026-07-06 |
| Business domain | `setting_core_engine` (application settings / chatbot theme configuration) |
| Target environment | local dev (PostgreSQL 17.10, Docker container `silvaengine-postgres`) |
| Approval status | `<pending confirmation>` |
| Test script | `setting_core_engine/tests/run_live_integration.py` |
| Pytest suite | `setting_core_engine/tests/test_postgresql_integration.py` |

## 2. Purpose and Scope

This SOP defines the ordered live integration scenarios used to validate
`setting_core_engine` through the **in-process GraphQL engine invocation**
pattern — calling `SettingCoreEngine.execute()` directly with
`DB_BACKEND=postgresql` against a live PostgreSQL database. This is the
same GraphQL execution path that the SilvaEngine Gateway dispatches to via
`setting_core_engine.main:dispatch_graphql`, but without the HTTP transport
layer.

- **In scope:**
  - All 2 persisted entities (`setting`, `theme_setting`) under
    `DB_BACKEND=postgresql`.
  - All GraphQL queries and mutations exposed by the `setting_core_engine`
    schema (Section 7).
  - Row-Level Security (RLS) enforcement on PostgreSQL backend
    (`set_rls_context` sets `app.tenant_id` from `partition_key` context).
  - Repository dispatch boundary — both entities resolve via `get_repo()`
    on both DynamoDB and PostgreSQL backends.
  - Static adoption guard — queries/ and mutations/ must not import
    backend-specific model modules directly.
  - JSONB `setting` field handling: `JSONSnakeCase` for `setting` entity,
    `JSONCamelCase` for `theme_setting` entity.
  - Nested resolvers on `ThemeSettingType` (`coordinations`, `agents`).
- **Out of scope:**
  - HTTP gateway transport testing (covered by a companion HTTP SOP if
    needed).
  - AWS Lambda async dispatch.
  - Live external LLM calls.
  - DynamoDB backend testing (PostgreSQL-first per project direction).
  - Production testing, destructive cleanup of production data.
  - Performance benchmarking beyond smoke-level timing.
- **System(s) under test:** `SettingCoreEngine` GraphQL engine and its
  persistence layer (`models/dynamodb`, `models/postgresql`,
  `models/repositories`).

## 2.1 Controlling End-to-End Testing Procedure

1. Execute the end-to-end live integration testing with the script
   `setting_core_engine/tests/run_live_integration.py`, which drives all
   GraphQL queries and mutations through `SettingCoreEngine.execute()`
   in-process.
2. Use variables from `setting_core_engine/tests/.env` to configure the
   database connection. Do not hard-code credentials in reports.
3. Before any scenario group is executed, verify that the `ping` query
   returns a valid response (INT-018, though run last as a smoke check).
4. Build the entity dependency map before execution (Section 6.1).
5. Perform end-to-end live integration testing in dependency order.
6. Address any implementation, runner, data-contract, or scenario-ordering
   issues found during live execution.
7. Retest affected scenarios, then rerun the full suite until all required
   calls pass with zero unexpected error responses.
8. Export the final per-function arguments and outputs into the project
   `docs/test_results/` directory.

## 3. Environment and Access

### 3.1 Test-Script Env Vars (read by `run_live_integration.py` and pytest)

| Item | Value / source |
|---|---|
| Environment target | local dev (PostgreSQL 17.10, Docker) |
| GraphQL invocation | in-process (`SettingCoreEngine.execute()`) |
| Credential source | `.env` variable names only; do not write secret values into reports |
| Required env vars | `region_name`, `aws_access_key_id`, `aws_secret_access_key`, `endpoint_id`, `part_id`, `db_backend`, `PG_HOST`, `PG_PORT`, `PG_USER`, `PG_PASSWORD`, `PG_DB`, `PG_TABLE_PREFIX`, `initialize_tables`, `cache_enabled` |
| Backend selection | `db_backend=postgresql` (set in `.env`) |
| RLS context | `set_rls_context(session, partition_key)` called before each GraphQL execution; `Config.db_session.remove()` after |

### 3.2 Database Configuration

| Item | Value |
|---|---|
| PostgreSQL host | `localhost` |
| PostgreSQL port | `5432` |
| Database name | `silvaengine` |
| Database user | `silvaengine` |
| Table prefix | `sce_` |
| Tables | `sce_settings` (0 rows), `sce_theme_settings` (15 rows) |
| RLS tables | `sce_settings`, `sce_theme_settings` |
| Endpoint ID | `gpt` |
| Part ID | `nestaging` |
| Partition key | `gpt#nestaging` |

## 4. Dependency Readiness Requirements

| Dependency | Type | Health check | Required readiness | Owner |
|---|---|---|---|---|
| Python environment | infrastructure | import `setting_core_engine` | operational | `bibow` |
| PostgreSQL 17.10 | infrastructure | `SELECT 1`; `sce_settings` and `sce_theme_settings` tables exist | operational | `bibow` |
| SQLAlchemy + psycopg2 | library | importable | installed | `bibow` |
| RLS policies (2 tables) | internal (module) | `tenant_isolation` policy on `sce_settings` and `sce_theme_settings` | operational | `bibow` |
| graphene + promise | library | import + schema builds | operational | open-source |
| Repository dispatch boundary | internal (module) | `get_repo("setting")` and `get_repo("theme_setting")` resolve under both backends | operational | SCE team |
| `silvaengine_dynamodb_base` | library | import + `BaseModel` meta initialized | operational | SilvaEngine team |
| `silvaengine_utility` | library | import + `Graphql` instantiable | operational | SilvaEngine team |
| `silvaengine_definitions` | library | import + `AgentLoader`, `CoordinationModel` accessible | operational | SilvaEngine team |
| AWS credentials | infrastructure | required for DynamoDB model class registration even in PG mode | configured | `bibow` |

## 5. Test Data Requirements

| Asset type | Count | Notes / constraints |
|---|---|---|
| Theme settings | 15 (pre-existing) | All `chatbotTheme` type under partition `gpt#nestaging`; used as read targets for INT-001/002 |
| Settings | 0 (pre-existing) | All test data created and cleaned up within scenarios |
| Test theme settings | 1 per CRUD scenario | Created and deleted within INT-003..009 |
| Test settings | 1 per CRUD scenario | Created and deleted within INT-011..017 |

- **Load order:** no dependency between entities — `setting` and `theme_setting` are independent root entities.
- **Data source:** pre-migrated from DynamoDB (`sce-theme_settings` had 15 rows; `sce-settings` had 0 rows). Test data generated by the test scripts through GraphQL mutations.
- **Cleanup:** each CRUD scenario creates a test record with a UUID, then deletes it. Final count checks (INT-009, INT-017) verify the database returns to its original state.

## 6. Execution Order

```text
[ping smoke (INT-018)] → [theme_setting CRUD (INT-001..009)] → [setting CRUD (INT-010..017)]
```

**Reason for ordering:** both entities are independent root entities with no
foreign key dependencies. Theme_setting is tested first because it has
pre-existing data (15 rows) that can be used for read validation. Setting is
tested second starting from an empty table. The `ping` query is run last as
a final smoke check but can also be run first.

### 6.1 Model Dependency Matrix

| # | Entity | Parent entity | FK field on child | Notes |
|---|---|---|---|---|
| 1 | theme_setting | — (root) | — | Tenant-partitioned; `setting` field is `JSONCamelCase`; has nested resolvers `coordinations` and `agents` |
| 2 | setting | — (root) | — | Tenant-partitioned; `setting` field is `JSONSnakeCase` |

### 6.2 Execution Sequence

#### Phase A: Infrastructure Verification

```text
1. Schema provisioning
   -> sce_settings and sce_theme_settings tables exist in PostgreSQL
   -> RLS policies (tenant_isolation) applied to both tables

2. Pre-existing data verification
   -> sce_theme_settings: 15 rows (pre-migrated from DynamoDB)
   -> sce_settings: 0 rows
```

#### Phase B: Transaction Testing

```text
3. theme_setting CRUD scenarios (INT-001 through INT-009)
   -> list query, single query, insert, query, update, query, delete, query, list count

4. setting CRUD scenarios (INT-010 through INT-017)
   -> list query, insert, query, update, query, delete, query, list count

5. Smoke test (INT-018)
   -> ping query
```

## 7. Integration Scenarios

### INT-001 — Query existing theme_setting list

| Field | Value |
|---|---|
| **ID** | INT-001 |
| **Name** | Query existing theme_setting list (should return 15) |
| **Priority** | P1 |
| **Type** | read / query |
| **CI trigger** | manual / pre-release |
| **Preconditions** | PostgreSQL running; 15 theme_settings pre-migrated |
| **Dependencies** | `theme_setting` repository; RLS context |
| **Test data** | none (uses pre-existing data) |
| **Steps** | 1. Set RLS context (`set_rls_context(session, "gpt#nestaging")`). 2. Execute `query { themeSettingList { total themeSettingList { themeUuid themeType themeTitle } } }`. 3. Verify `total == 15`. |
| **Expected behavior** | `themeSettingList.total` returns 15; `themeSettingList.themeSettingList` has 15 items |
| **Validation points** | list_returns_15, total_matches_count |

### INT-002 — Query single theme_setting by uuid

| Field | Value |
|---|---|
| **ID** | INT-002 |
| **Name** | Query single theme_setting by uuid |
| **Priority** | P1 |
| **Type** | read / query |
| **CI trigger** | manual / pre-release |
| **Preconditions** | INT-001 passed (list available to pick uuid from) |
| **Dependencies** | `theme_setting` repository; RLS context |
| **Test data** | uuid picked from INT-001 list result |
| **Steps** | 1. Pick first `themeUuid` from INT-001 list. 2. Set RLS context. 3. Execute `query Q($uuid: String!) { themeSetting(themeUuid: $uuid) { themeUuid themeType themeTitle } }`. 4. Verify returned `themeUuid` matches. |
| **Expected behavior** | `themeSetting` returns a non-null object with matching `themeUuid` |
| **Validation points** | single_query_returns_data, uuid_matches |

### INT-003 — Insert new theme_setting

| Field | Value |
|---|---|
| **ID** | INT-003 |
| **Name** | Insert new theme_setting (type=chatbotTheme) |
| **Priority** | P1 |
| **Type** | create / mutation |
| **CI trigger** | manual / pre-release |
| **Preconditions** | PostgreSQL running; RLS context |
| **Dependencies** | `theme_setting` repository; `JSONCamelCase` scalar |
| **Test data** | `themeType=chatbotTheme`, `themeTitle="Integration Test Theme"`, `setting={primaryColor: "#ff0000", fontSize: 14}` |
| **Steps** | 1. Set RLS context. 2. Execute `mutation I($tu: String, $tt: String!, $title: String, $desc: String, $setting: JSONCamelCase!, $by: String) { insertUpdateThemeSetting(...) }` with test data. 3. Verify returned `themeType == "chatbotTheme"` and `themeTitle == "Integration Test Theme"`. |
| **Expected behavior** | Mutation returns `themeSetting` type with correct `themeType` and `themeTitle` |
| **Validation points** | insert_returns_type, theme_type_correct, theme_title_correct |

### INT-004 — Query the new theme_setting

| Field | Value |
|---|---|
| **ID** | INT-004 |
| **Name** | Query the newly inserted theme_setting |
| **Priority** | P1 |
| **Type** | read / query |
| **CI trigger** | manual / pre-release |
| **Preconditions** | INT-003 passed (theme_setting exists) |
| **Dependencies** | `theme_setting` repository; RLS context |
| **Test data** | uuid from INT-003 |
| **Steps** | 1. Set RLS context. 2. Execute `query Q($uuid: String!) { themeSetting(themeUuid: $uuid) { themeUuid themeType themeTitle themeDescription } }`. 3. Verify `themeUuid` matches and `themeTitle == "Integration Test Theme"`. |
| **Expected behavior** | `themeSetting` returns non-null with matching uuid and title |
| **Validation points** | query_returns_data, title_matches_inserted |

### INT-005 — Update the theme_setting

| Field | Value |
|---|---|
| **ID** | INT-005 |
| **Name** | Update the theme_setting (change title) |
| **Priority** | P1 |
| **Type** | update / mutation |
| **CI trigger** | manual / pre-release |
| **Preconditions** | INT-003 passed (theme_setting exists) |
| **Dependencies** | `theme_setting` repository; `JSONCamelCase` scalar |
| **Test data** | same uuid; `themeTitle="Integration Test Theme Updated"`, `setting={primaryColor: "#00ff00", fontSize: 16}` |
| **Steps** | 1. Set RLS context. 2. Execute `mutation U(...)` with updated title and setting. 3. Verify returned `themeTitle == "Integration Test Theme Updated"`. |
| **Expected behavior** | Mutation returns updated `themeTitle` |
| **Validation points** | update_changes_title, update_returns_type |

### INT-006 — Query updated theme_setting

| Field | Value |
|---|---|
| **ID** | INT-006 |
| **Name** | Query updated theme_setting (verify title changed) |
| **Priority** | P1 |
| **Type** | read / query |
| **CI trigger** | manual / pre-release |
| **Preconditions** | INT-005 passed (update applied) |
| **Dependencies** | `theme_setting` repository; RLS context |
| **Test data** | uuid from INT-003 |
| **Steps** | 1. Set RLS context. 2. Execute query for the theme_setting. 3. Verify `themeTitle == "Integration Test Theme Updated"`. |
| **Expected behavior** | Query returns the updated title |
| **Validation points** | query_reflects_update |

### INT-007 — Delete the test theme_setting

| Field | Value |
|---|---|
| **ID** | INT-007 |
| **Name** | Delete the test theme_setting |
| **Priority** | P1 |
| **Type** | delete / mutation |
| **CI trigger** | manual / pre-release |
| **Preconditions** | INT-003 passed (theme_setting exists) |
| **Dependencies** | `theme_setting` repository; RLS context |
| **Test data** | uuid from INT-003 |
| **Steps** | 1. Set RLS context. 2. Execute `mutation D($tu: String!) { deleteThemeSetting(themeUuid: $tu) { ok } }`. 3. Verify `ok == true`. |
| **Expected behavior** | `deleteThemeSetting.ok` returns `true` |
| **Validation points** | delete_returns_true |

### INT-008 — Query deleted theme_setting

| Field | Value |
|---|---|
| **ID** | INT-008 |
| **Name** | Query deleted theme_setting (should return null) |
| **Priority** | P1 |
| **Type** | read / query |
| **CI trigger** | manual / pre-release |
| **Preconditions** | INT-007 passed (theme_setting deleted) |
| **Dependencies** | `theme_setting` repository; RLS context |
| **Test data** | uuid from INT-003 |
| **Steps** | 1. Set RLS context. 2. Execute query for the deleted theme_setting. 3. Verify `themeSetting == null`. |
| **Expected behavior** | `themeSetting` returns `null` |
| **Validation points** | deleted_returns_null |

### INT-009 — theme_setting_list count after delete

| Field | Value |
|---|---|
| **ID** | INT-009 |
| **Name** | theme_setting_list count after delete (should be back to 15) |
| **Priority** | P1 |
| **Type** | read / query |
| **CI trigger** | manual / pre-release |
| **Preconditions** | INT-007 passed (test record deleted) |
| **Dependencies** | `theme_setting` repository; RLS context |
| **Test data** | none |
| **Steps** | 1. Set RLS context. 2. Execute `query { themeSettingList { total } }`. 3. Verify `total == 15`. |
| **Expected behavior** | `total` returns 15 (original count restored) |
| **Validation points** | count_restored_to_15 |

### INT-010 — Query setting list (should return 0)

| Field | Value |
|---|---|
| **ID** | INT-010 |
| **Name** | Query setting list (should return 0) |
| **Priority** | P1 |
| **Type** | read / query |
| **CI trigger** | manual / pre-release |
| **Preconditions** | PostgreSQL running; 0 settings pre-existing |
| **Dependencies** | `setting` repository; RLS context |
| **Test data** | none |
| **Steps** | 1. Set RLS context. 2. Execute `query { settingList { total settingList { settingUuid } } }`. 3. Verify `total == 0`. |
| **Expected behavior** | `settingList.total` returns 0 |
| **Validation points** | list_returns_0 |

### INT-011 — Insert new setting

| Field | Value |
|---|---|
| **ID** | INT-011 |
| **Name** | Insert new setting (type=test_config) |
| **Priority** | P1 |
| **Type** | create / mutation |
| **CI trigger** | manual / pre-release |
| **Preconditions** | PostgreSQL running; RLS context |
| **Dependencies** | `setting` repository; `JSONSnakeCase` scalar |
| **Test data** | `settingType=test_config`, `setting={key: "value", nested: {foo: "bar"}}`, `updatedBy=tester` |
| **Steps** | 1. Set RLS context. 2. Execute `mutation I($su: String, $st: String!, $setting: JSONSnakeCase!, $by: String) { insertUpdateSetting(...) }`. 3. Verify returned `settingType == "test_config"`. |
| **Expected behavior** | Mutation returns `setting` type with correct `settingType` |
| **Validation points** | insert_returns_type, setting_type_correct |

### INT-012 — Query the new setting

| Field | Value |
|---|---|
| **ID** | INT-012 |
| **Name** | Query the new setting |
| **Priority** | P1 |
| **Type** | read / query |
| **CI trigger** | manual / pre-release |
| **Preconditions** | INT-011 passed (setting exists) |
| **Dependencies** | `setting` repository; RLS context |
| **Test data** | uuid from INT-011 |
| **Steps** | 1. Set RLS context. 2. Execute `query Q($uuid: String!) { setting(settingUuid: $uuid) { settingUuid settingType } }`. 3. Verify `settingUuid` matches. |
| **Expected behavior** | `setting` returns non-null with matching uuid |
| **Validation points** | query_returns_data, uuid_matches |

### INT-013 — Update the setting

| Field | Value |
|---|---|
| **ID** | INT-013 |
| **Name** | Update the setting (change setting data) |
| **Priority** | P1 |
| **Type** | update / mutation |
| **CI trigger** | manual / pre-release |
| **Preconditions** | INT-011 passed (setting exists) |
| **Dependencies** | `setting` repository; `JSONSnakeCase` scalar |
| **Test data** | same uuid; `setting={key: "new_value", extra: true}` |
| **Steps** | 1. Set RLS context. 2. Execute update mutation with new setting data. 3. Verify mutation succeeds. |
| **Expected behavior** | Mutation returns updated `setting` type |
| **Validation points** | update_returns_type |

### INT-014 — Query updated setting

| Field | Value |
|---|---|
| **ID** | INT-014 |
| **Name** | Query updated setting |
| **Priority** | P1 |
| **Type** | read / query |
| **CI trigger** | manual / pre-release |
| **Preconditions** | INT-013 passed (update applied) |
| **Dependencies** | `setting` repository; RLS context |
| **Test data** | uuid from INT-011 |
| **Steps** | 1. Set RLS context. 2. Execute query for the setting. 3. Verify `settingUuid` matches. |
| **Expected behavior** | Query returns the setting with matching uuid |
| **Validation points** | query_reflects_update |

### INT-015 — Delete the test setting

| Field | Value |
|---|---|
| **ID** | INT-015 |
| **Name** | Delete the test setting |
| **Priority** | P1 |
| **Type** | delete / mutation |
| **CI trigger** | manual / pre-release |
| **Preconditions** | INT-011 passed (setting exists) |
| **Dependencies** | `setting` repository; RLS context |
| **Test data** | uuid from INT-011 |
| **Steps** | 1. Set RLS context. 2. Execute `mutation D($su: String!) { deleteSetting(settingUuid: $su) { ok } }`. 3. Verify `ok == true`. |
| **Expected behavior** | `deleteSetting.ok` returns `true` |
| **Validation points** | delete_returns_true |

### INT-016 — Query deleted setting

| Field | Value |
|---|---|
| **ID** | INT-016 |
| **Name** | Query deleted setting (should return null) |
| **Priority** | P1 |
| **Type** | read / query |
| **CI trigger** | manual / pre-release |
| **Preconditions** | INT-015 passed (setting deleted) |
| **Dependencies** | `setting` repository; RLS context |
| **Test data** | uuid from INT-011 |
| **Steps** | 1. Set RLS context. 2. Execute query for the deleted setting. 3. Verify `setting == null`. |
| **Expected behavior** | `setting` returns `null` |
| **Validation points** | deleted_returns_null |

### INT-017 — setting_list count after delete

| Field | Value |
|---|---|
| **ID** | INT-017 |
| **Name** | setting_list count after delete (should be 0) |
| **Priority** | P1 |
| **Type** | read / query |
| **CI trigger** | manual / pre-release |
| **Preconditions** | INT-015 passed (test record deleted) |
| **Dependencies** | `setting` repository; RLS context |
| **Test data** | none |
| **Steps** | 1. Set RLS context. 2. Execute `query { settingList { total } }`. 3. Verify `total == 0`. |
| **Expected behavior** | `total` returns 0 (original count restored) |
| **Validation points** | count_restored_to_0 |

### INT-018 — Ping query

| Field | Value |
|---|---|
| **ID** | INT-018 |
| **Name** | Ping query (smoke test) |
| **Priority** | P0 |
| **Type** | smoke |
| **CI trigger** | every run |
| **Preconditions** | Engine initialized |
| **Dependencies** | `SettingCoreEngine.build_graphql_schema()` |
| **Test data** | none |
| **Steps** | 1. Execute `query { ping }`. 2. Verify response contains "Hello". |
| **Expected behavior** | `ping` returns a greeting string containing "Hello" |
| **Validation points** | ping_returns_greeting |

## 8. Resilience Scenarios

| ID | Name | Priority | Steps | Expected behavior |
|---|---|---|---|---|
| RES-001 | Query non-existent theme_setting | P2 | Query `themeSetting(themeUuid: "nonexistent-uuid")` | Returns `null`, no error |
| RES-002 | Query non-existent setting | P2 | Query `setting(settingUuid: "nonexistent-uuid")` | Returns `null`, no error |
| RES-003 | Delete non-existent theme_setting | P2 | Mutation `deleteThemeSetting(themeUuid: "nonexistent-uuid")` | Returns `ok: true` (idempotent) |
| RES-004 | Delete non-existent setting | P2 | Mutation `deleteSetting(settingUuid: "nonexistent-uuid")` | Returns `ok: true` (idempotent) |

## 9. Reconciliation

| ID | Name | Check | Expected |
|---|---|---|---|
| REC-001 | theme_setting count consistency | `themeSettingList.total` after all CRUD | 15 (original) |
| REC-002 | setting count consistency | `settingList.total` after all CRUD | 0 (original) |
| REC-003 | Backend parity | Both entities resolve via `get_repo()` on both DynamoDB and PostgreSQL | All entities resolve |

## 10. Exit Criteria

- All P0 and P1 scenarios pass with zero unexpected error responses.
- All pytest tests pass (`test_backend_agnostic_dispatch.py`, `test_repository_adoption_guard.py`, `test_postgresql_integration.py`).
- Live call log generated at `docs/test_results/live_call_log.json`.
- Certification report generated at `docs/test_results/integration_certification_report.md`.
- No test data left behind (count checks INT-009 and INT-017 confirm original state).

## 11. Deliverables

| Deliverable | Path |
|---|---|
| SOP document | `docs/integration_scenarios_sop.md` |
| Pytest config | `setting_core_engine/tests/pytest.ini` |
| Test fixtures | `setting_core_engine/tests/conftest.py` |
| Dispatch tests | `setting_core_engine/tests/test_backend_agnostic_dispatch.py` |
| Guard tests | `setting_core_engine/tests/test_repository_adoption_guard.py` |
| Integration tests | `setting_core_engine/tests/test_postgresql_integration.py` |
| Live runner | `setting_core_engine/tests/run_live_integration.py` |
| Call log | `docs/test_results/live_call_log.json` |
| Certification report | `docs/test_results/integration_certification_report.md` |