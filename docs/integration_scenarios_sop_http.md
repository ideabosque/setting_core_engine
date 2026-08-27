# Continuous Integration Scenarios SOP — Setting Core Engine (HTTP Gateway Transport)

## 1. Document Control

| Field | Value |
|---|---|
| SOP title | Setting Core Engine Live Integration SOP — HTTP Gateway Transport (GraphQL over REST) |
| Version | 0.1.0 |
| Owner / contact | `bibow` |
| Last updated | 2026-07-07 |
| Business domain | `setting_core` (application settings / chatbot theme configuration) |
| Target environment | local dev gateway instance using `setting_core_engine/tests/.env` |
| Approval status | `<pending confirmation>` |
| Companion SOP | `integration_scenarios_sop.md` (direct in-process GraphQL engine invocation) |
| Test script | `setting_core_engine/tests/run_http_integration.py` |

## 2. Purpose and Scope

This SOP defines the ordered live integration scenarios used to validate
`setting_core_engine` through the **HTTP gateway transport layer** — the
same GraphQL-over-REST path (`POST /{endpoint_id}/setting_core_graphql`)
that a real client (AI agent, frontend, or external service) uses to invoke
queries and mutations via the `silvaengine_gateway`. Unlike the companion
SOP (which calls `SettingCoreEngine.execute()` directly in-process with
`DB_BACKEND` set per invocation), this SOP exercises only the
`HTTP client → gateway /setting_core_graphql → dispatch_graphql →
SettingCoreEngine` path. The gateway handles Config initialization, JWT
Bearer auth, tenant routing via `Part-Id` header, and request/response
serialization internally.

- **In scope:**
  - All 2 persisted entities (`theme_setting`, `setting`) through the gateway GraphQL endpoint.
  - All GraphQL queries and mutations exposed by the `setting_core_engine`
    schema (Section 7).
  - Gateway JWT Bearer auth flow (`POST /auth/token` → JWT → `Authorization`
    header on all GraphQL requests).
  - Tenant routing via `Part-Id` request header (gateway builds
    `partition_key = {endpoint_id}#{part_id}`).
  - `DB_BACKEND` configured at gateway startup via `Config.initialize`; both
    `dynamodb` and `postgresql` backends exercisable by restarting the gateway
    with different `.env` settings.
  - RLS (Row-Level Security) enforcement on PostgreSQL backend (gateway sets
    `app.tenant_id` from `partition_key` context).
  - JSONB `setting` field handling: `JSONCamelCase` for `theme_setting`
    entity, `JSONSnakeCase` for `setting` entity.
  - Nested resolvers on `ThemeSettingType` (`coordinations`, `agents`).
  - Gateway error handling: HTTP status codes, GraphQL error envelopes,
    connection failures, auth failures.
- **Out of scope:**
  - Direct in-process method calls on `SettingCoreEngine` (covered by
    companion SOP `integration_scenarios_sop.md`).
  - AWS Lambda async dispatch mechanism.
  - Live external LLM calls.
  - DynamoDB-to-PostgreSQL data migration.
  - Production testing, destructive cleanup of generated live test records,
    cloud provisioning, third-party production side effects, UI testing, load
    testing.
  - Performance benchmarking beyond smoke-level timing.
- **System(s) under test:** `silvaengine_gateway` REST GraphQL route
  (`/{endpoint_id}/setting_core_graphql` with `Part-Id` request header),
  `setting_core_engine.main:dispatch_graphql`, `SettingCoreEngine`
  GraphQL engine and its persistence layer (`models/dynamodb`,
  `models/postgresql`, `models/repositories`).
- **Transport validation:** this SOP validates that the gateway correctly
  dispatches GraphQL POST requests to `dispatch_graphql`, which instantiates
  `SettingCoreEngine`, executes the GraphQL schema, and returns the
  response as HTTP JSON `{data, errors}`. The test script never accesses the
  engine or database directly.

## 2.1 Controlling End-to-End Testing Procedure

The following procedure is authoritative for this HTTP gateway transport SOP:

1. Execute the end-to-end live integration testing with the script
   `setting_core_engine/tests/run_http_integration.py`, which uses an
   HTTP client (`requests`) to drive all GraphQL queries and mutations
   through the gateway REST endpoint
   `POST /{endpoint_id}/setting_core_graphql`.
2. Use variables from `setting_core_engine/tests/.env` to target the local
   gateway instance. Do not hard-code credentials, endpoint IDs, partition
   IDs, or gateway URLs in generated reports.
3. Before any scenario group is executed, verify that the HTTP client can
   successfully complete the gateway auth flow (`POST /auth/token` → JWT) and
   that a `ping` query returns a valid response. This confirms the transport
   layer is operational.
4. Optionally run schema introspection to verify that the GraphQL schema
   returns the expected queries and mutations before proceeding to scenario
   execution.
5. Build the entity dependency map before execution, then derive the test
   sequence priority from that dependency map rather than file-discovery
   order.
6. Perform end-to-end live integration testing in dependency order via
   GraphQL POST invocations.
7. Address any implementation, runner, data-contract, HTTP transport, or
   scenario-ordering issues found during live execution.
8. Retest affected scenarios, then rerun the full dependency-ordered suite
   until all required calls pass with zero unexpected error responses.
9. Export the final per-function arguments and outputs into the project
   `docs/` directory.

## 3. Environment and Access

> **Env var split.** There are two distinct `.env` scopes: **test-script env
> vars** (read by `run_http_integration.py` for HTTP connection) and
> **gateway-startup env vars** (read by the gateway process at boot for backend
> configuration). The test script does NOT read or set `DB_BACKEND`,
> `DATABASE_URL`, `PG_*`, or backend credentials — those are gateway-startup
> settings. To switch backends, restart the gateway with different startup
> env vars.

### 3.1 Test-Script Env Vars (read by `run_http_integration.py`)

| Item | Value / source |
|---|---|
| Environment target | local dev gateway instance |
| GraphQL REST endpoint | `GRAPHQL_URL` from `.env`, default `{GATEWAY_BASE_URL}/{endpoint_id}/setting_core_graphql` |
| Credential source | `.env` variable names only; do not write secret values into reports |
| Auth flow | HTTP client obtains JWT Bearer token from `{GATEWAY_BASE_URL}/auth/token` using `TOKEN_USERNAME` / `TOKEN_PASSWORD`; token is sent as `Authorization: Bearer ***` header on all GraphQL POST requests |
| Required env vars | `GATEWAY_BASE_URL`, `TOKEN_USERNAME`, `TOKEN_PASSWORD`, `endpoint_id`, `part_id` |
| HTTP client config | `base_url` = `GATEWAY_BASE_URL`, `graphql_endpoint` = `{base_url}/{endpoint_id}/setting_core_graphql`, `bearer_token` = gateway JWT, `headers` = `{"Part-Id": PART_ID}` |

### 3.2 Gateway-Startup Env Vars (read by the gateway process at boot)

| Item | Value / source |
|---|---|
| Data stores | DynamoDB (`sce_*` tables, 2 tables); PostgreSQL (2 tables, SQLAlchemy + Alembic) — configured at gateway startup, not per-request |
| Backend selection | `DB_BACKEND=dynamodb` or `DB_BACKEND=postgresql`; set at gateway startup; restart gateway to switch |
| DynamoDB credentials | `region_name`, `aws_access_key_id`, `aws_secret_access_key` (DynamoDB mode) |
| PostgreSQL credentials | `DATABASE_URL` or `PG_HOST` / `PG_PORT` / `PG_USER` / `PG_PASSWORD` / `PG_DB` (PostgreSQL mode) |
| Table prefix | `PG_TABLE_PREFIX=sce_` (PostgreSQL mode) |
| Access constraints | local process access to gateway; `setting_core_engine` module must be loaded into gateway via `routes.yaml` |
| Provisioning policy | auto-provision PG schema (`alembic upgrade head` or `Base.metadata.create_all`) at gateway startup; manual approval required for any cloud credential scope change or production access |

### 3.3 Gateway Route Configuration

| Item | Value |
|---|---|
| Route path | `/{endpoint_id}/setting_core_graphql` |
| Handler type | `graphql` |
| Dispatch function | `setting_core_engine.main:dispatch_graphql` |
| Auth | `true` (JWT Bearer required) |
| Config class | `setting_core_engine.handlers.config:Config` |
| Config init style | `kwargs` — gateway calls `Config.initialize(logger, **setting)` |
| `Part-Id` header | not part of the URL; sent in `Part-Id` request header; gateway builds `partition_key = {endpoint_id}#{Part-Id}` |
| Session lifecycle | `dispatch_graphql` wraps each request with `try/except: db_session.rollback()` + `finally: db_session.remove()` — automatic scoped-session cleanup on PostgreSQL; no stale session state across HTTP requests |

> **Names and sources only — never paste secrets, tokens, or connection strings.**

## 4. Dependency Readiness Requirements

| Dependency | Type | Health check | Required readiness | Owner |
|---|---|---|---|---|
| Python environment | infrastructure | import HTTP client and `run_http_integration` module | operational | `bibow` |
| `requests` | library | importable (required for HTTP) | installed | `bibow` |
| `python-dotenv` | library | importable (required for `.env` loading) | installed | `bibow` |
| `silvaengine_gateway` local instance | internal | `POST /auth/token` returns JWT; `POST /{endpoint_id}/setting_core_graphql` with `ping` query returns `"Hello at ..."` | operational | `bibow` |
| `setting_core_engine` module loaded | internal | GraphQL `ping` query returns valid response via gateway | loaded and operational | `bibow` |
| DynamoDB (`sce_*` tables) | infrastructure | `initialize_tables(logger)` succeeds at gateway startup | operational (if `DB_BACKEND=dynamodb`) | `bibow` |
| PostgreSQL (`sce_*` tables) | infrastructure | `DATABASE_URL` reachable; `SELECT 1`; `alembic upgrade head` or `Base.metadata.create_all` at gateway startup | initialized (if `DB_BACKEND=postgresql`) | `bibow` |
| Repository dispatch boundary | internal (module) | `get_repo("theme_setting")` and `get_repo("setting")` resolve under active backend | operational | SCE team |
| `silvaengine_utility` | internal (library) | import + `JSONCamelCase`, `JSONSnakeCase` usable | operational | SilvaEngine team |
| `silvaengine_dynamodb_base` | internal (library) | import + `ListObjectType` meta initialized | operational | SilvaEngine team |
| `graphene` / `promise` | internal (library) | import + schema builds | operational | open-source |
| `SQLAlchemy>=1.4` / `psycopg2-binary` / `alembic` | internal (library, PG-only) | import; installed via project extras | configured | open-source |

## 5. Test Data Requirements

| Asset type | Count | Notes / constraints |
|---|---|---|
| Theme settings | 2+ | At least one `chatbotTheme` and one `dashboardTheme` for filter testing |
| Settings | 1+ | One `globalConfig` type with nested JSON snake_case keys |
| Users / roles | 1 | Admin (`admin`) — used as `updated_by` |

- **Load order:** theme settings and settings are independent entities; no parent-child dependency between them.
- **Data source:** generated by the test script driving data through the gateway GraphQL endpoint via HTTP POST — the same mutations production traffic uses. Scripts are backend-agnostic: the active backend is determined by gateway startup `DB_BACKEND` config.

### Existing Data

- 15 theme_settings in PostgreSQL (`sce_theme_settings` table), all `type=chatbotTheme`, `pk=gpt#nestaging`.
- 0 settings in `sce_settings` table.

**Prerequisites:**
- Gateway `.env` configured with `endpoint_id`, `part_id`, and backend-specific credentials
- For PostgreSQL: `alembic upgrade head` applied before gateway startup (schema must exist before data loading)
- Gateway running and reachable at `GATEWAY_BASE_URL`
- `setting_core_engine` loaded into gateway via `routes.yaml`

## 6. Execution Order

```text
[auth handshake + ping (INT-HTTP-000)] → [auth failure (INT-HTTP-001)] → [tenant isolation (INT-HTTP-002)] → theme_setting CRUD → setting CRUD → theme_setting list filters
```

**Reason for ordering:** `theme_setting` and `setting` are independent root entities with no parent-child dependency. The gateway auth handshake and `ping` query are implicit first steps — the HTTP client obtains a JWT and verifies connectivity before any scenario executes. Tenant isolation is validated before CRUD to confirm the partition context is correct.

**Sequence construction rule:** the execution order must be rebuilt or revalidated before each certification run from the actual entity dependencies in the schema and codebase. Static file order is not sufficient.

### 6.1 Model Dependency Matrix

| # | Child entity | Parent entity | FK field on child | Notes |
|---|---|---|---|---|
| 1 | ThemeSetting | — (root) | — | Tenant-partitioned (hash=partition_key); contains `setting` JSONCamelCase field |
| 2 | Setting | — (root) | — | Tenant-partitioned (hash=partition_key); contains `setting` JSONSnakeCase field |

### 6.2 Execution Sequence

The certification run proceeds in two phases: **asset loading** and
**transaction testing**. All test assets must be loaded and validated before
any transaction scenario executes.

#### Phase A: Asset Loading (must complete before Phase B)

```text
1. Schema provisioning
   -> alembic upgrade head (PostgreSQL) or initialize_tables (DynamoDB)
   -> gateway started with correct DB_BACKEND

2. Asset validation gate:
   -> row counts per table > 0 for theme_settings (15 existing)
   -> settings table empty (0 existing)
   -> referential integrity clean
```

#### Phase B: Transaction Testing (executes after Phase A gate passes)

```text
3. Transport smoke (INT-HTTP-000)
   -> auth handshake, ping query, schema introspection

4. Security scenarios (INT-HTTP-001, INT-HTTP-002)
   -> auth failure, tenant isolation

5. Entity CRUD scenarios (INT-HTTP-003, INT-HTTP-004)
   -> theme_setting CRUD, setting CRUD

6. Filter scenarios (INT-HTTP-005)
   -> theme_setting list with type filter

7. Resilience scenarios (Section 8)
   -> missing data, invalid data, auth failures, gateway failures

8. Reconciliation (Section 9)
   -> referential integrity, count consistency
```

### 6.3 Transaction Scenario Dependency Graph

```text
INT-HTTP-000 (transport smoke) --> all scenarios
INT-HTTP-001 (auth failure) -----> INT-HTTP-003+ (requires valid auth first)
INT-HTTP-002 (tenant isolation) --> all CRUD scenarios
     |
     v
INT-HTTP-003 (theme_setting CRUD) -- independent
INT-HTTP-004 (setting CRUD) ------- independent
INT-HTTP-005 (theme_setting list filters) --> depends on INT-HTTP-003 pattern
```

## 7. Integration Scenarios

### INT-HTTP-000 — Gateway transport initialization and smoke test

| Field | Value |
|---|---|
| **ID** | INT-HTTP-000 |
| **Name** | Gateway auth handshake, ping query, and schema introspection |
| **Priority** | P0 |
| **Type** | transport / smoke |
| **CI trigger** | manual / pre-release |
| **Preconditions** | Gateway is running; `setting_core_engine` is loaded via `routes.yaml` |
| **Dependencies** | gateway, `dispatch_graphql`, `Config.initialize` |
| **Test data** | none (transport handshake only) |
| **Steps** | 1. `POST /auth/token` with `TOKEN_USERNAME` / `TOKEN_PASSWORD` → verify JWT returned. 2. `POST /{endpoint_id}/setting_core_graphql` with `Authorization: Bearer ***`, `Part-Id: ***`, body `{"query": "{ ping }"}` → verify response `{"data": {"ping": "Hello at ..."}}`. 3. Introspect schema: `{"query": "{ __schema { queryType { fields { name } } mutationType { fields { name } } } }"}` → verify expected query/mutation names. |
| **Expected behavior** | JWT obtained; `ping` returns greeting string; schema introspection returns all expected queries (`ping`, `themeSetting`, `themeSettingList`, `setting`, `settingList`) and mutations (`insertUpdateThemeSetting`, `deleteThemeSetting`, `insertUpdateSetting`, `deleteSetting`) |
| **Validation points** | jwt_obtained, ping_returns_greeting, schema_introspection_complete |
| **Cross-system checks** | gateway correctly resolves `setting_core_engine.main:dispatch_graphql` and `Config.initialize` succeeds with `config_init_style: kwargs` |

### INT-HTTP-001 — Auth failure (missing/invalid Bearer token)

| Field | Value |
|---|---|
| **ID** | INT-HTTP-001 |
| **Name** | Missing or invalid JWT Bearer token returns 401 |
| **Priority** | P0 |
| **Type** | transport / security |
| **CI trigger** | manual / pre-release |
| **Preconditions** | Gateway is running; `setting_core_engine` is loaded |
| **Dependencies** | gateway auth middleware |
| **Test data** | none |
| **Steps** | 1. `POST /{endpoint_id}/setting_core_graphql` with no `Authorization` header → verify HTTP 401. 2. `POST /{endpoint_id}/setting_core_graphql` with `Authorization: Bearer invalid-token` → verify HTTP 401. |
| **Expected behavior** | Gateway rejects unauthenticated requests with 401; invalid tokens rejected; no GraphQL execution occurs without valid auth |
| **Validation points** | missing_token_rejected, invalid_token_rejected |
| **Cross-system checks** | Gateway auth middleware active on `setting_core_graphql` route |

### INT-HTTP-002 — Tenant isolation via Part-Id header

| Field | Value |
|---|---|
| **ID** | INT-HTTP-002 |
| **Name** | Same query with different `Part-Id` headers returns different tenant's data |
| **Priority** | P1 |
| **Type** | transport / tenant isolation |
| **CI trigger** | nightly |
| **Preconditions** | INT-HTTP-000 passed |
| **Dependencies** | gateway `Part-Id` header routing; `partition_key` context |
| **Test data** | 1 theme setting created under tenant A (`Part-Id: nestaging`); 1 theme setting under tenant B (`Part-Id: neprodai`) |
| **Steps** | 1. `POST` mutation `insertUpdateThemeSetting` with `Part-Id: nestaging` → create theme setting A. 2. `POST` mutation `insertUpdateThemeSetting` with `Part-Id: neprodai` → create theme setting B. 3. `POST` query `themeSettingList` with `Part-Id: nestaging` → verify only tenant A's data is returned (theme setting B not in list). 4. `POST` query `themeSetting(themeUuid: <A>)` with `Part-Id: neprodai` → verify returns `null` (wrong tenant). 5. Cleanup both theme settings. |
| **Expected behavior** | Gateway builds `partition_key` from `Part-Id` header; each tenant sees only its own data; cross-tenant queries return `null` or empty lists |
| **Validation points** | tenant_a_isolated, tenant_b_isolated, cross_tenant_query_null |
| **Cross-system checks** | `partition_key` in response context matches `{endpoint_id}#{Part-Id}`; no tenant data leakage |

### INT-HTTP-003 — Theme Setting CRUD via HTTP

| Field | Value |
|---|---|
| **ID** | INT-HTTP-003 |
| **Name** | Create, read, update, delete a theme setting through gateway GraphQL |
| **Priority** | P1 |
| **Type** | end-to-end (HTTP) |
| **CI trigger** | manual / pre-release |
| **Preconditions** | INT-HTTP-000 passed; gateway running with active backend |
| **Dependencies** | `theme_setting` repository; gateway GraphQL dispatch |
| **Test data** | 1 theme setting with `JSONCamelCase` setting field (nested object with `primaryColor`, `features`, etc.) |
| **Steps** | 1. `POST` mutation `insertUpdateThemeSetting` with `themeUuid`, `themeType`, `themeTitle`, `themeDescription`, `setting` (JSONCamelCase object), `updatedBy`. 2. `POST` query `themeSetting(themeUuid: ...)` verify all fields including `createdAt`, `updatedAt`. 3. `POST` mutation `insertUpdateThemeSetting` update `themeTitle` and `setting`. 4. `POST` query `themeSettingList(themeType: ...)` verify created theme setting in list. 5. `POST` mutation `deleteThemeSetting` verify `ok == true`. 6. `POST` query `themeSetting` verify `null`. |
| **Expected behavior** | Insert returns theme setting type; get returns all fields; update changes title and setting; list returns correct entries; delete returns true; post-delete get returns null |
| **Validation points** | insert_returns_type, get_returns_fields, update_changes_title_and_setting, list_returns_entries, delete_returns_true, post_delete_null |
| **Cross-system checks** | `setting` field is `JSONCamelCase` — returned as JSON object, not sub-field selectable; `updated_at` advances on update; HTTP response is valid JSON `{data, errors}` with `errors: null` |

### INT-HTTP-004 — Setting CRUD via HTTP

| Field | Value |
|---|---|
| **ID** | INT-HTTP-004 |
| **Name** | Create, read, update, delete a setting through gateway GraphQL |
| **Priority** | P1 |
| **Type** | end-to-end (HTTP) |
| **CI trigger** | manual / pre-release |
| **Preconditions** | INT-HTTP-000 passed; gateway running with active backend |
| **Dependencies** | `setting` repository; gateway GraphQL dispatch |
| **Test data** | 1 setting with `JSONSnakeCase` setting field (nested object with `max_retries`, `feature_flags`, etc.) |
| **Steps** | 1. `POST` mutation `insertUpdateSetting` with `settingUuid`, `settingType`, `setting` (JSONSnakeCase object), `updatedBy`. 2. `POST` query `setting(settingUuid: ...)` verify all fields including `createdAt`, `updatedAt`. 3. `POST` mutation `insertUpdateSetting` update `setting` field. 4. `POST` query `settingList(settingType: ...)` verify created setting in list. 5. `POST` mutation `deleteSetting` verify `ok == true`. 6. `POST` query `setting` verify `null`. |
| **Expected behavior** | Insert returns setting type; get returns all fields; update changes setting field; list returns correct entries; delete returns true; post-delete get returns null |
| **Validation points** | insert_returns_type, get_returns_fields, update_changes_setting, list_returns_entries, delete_returns_true, post_delete_null |
| **Cross-system checks** | `setting` field is `JSONSnakeCase` — returned as JSON object with snake_case keys; numeric values may be serialized as strings (JSONSnakeCase behavior); `updated_at` advances on update; HTTP response is valid JSON `{data, errors}` with `errors: null` |

### INT-HTTP-005 — Theme Setting list with type filter via HTTP

| Field | Value |
|---|---|
| **ID** | INT-HTTP-005 |
| **Name** | `themeSettingList` filtering by `themeType` returns correct subsets through gateway GraphQL |
| **Priority** | P2 |
| **Type** | end-to-end (filter / HTTP) |
| **CI trigger** | nightly |
| **Preconditions** | INT-HTTP-000 passed; theme settings exist with varied `theme_type` |
| **Dependencies** | `theme_setting` repository; gateway GraphQL dispatch |
| **Test data** | 2 theme settings: one `chatbotTheme`, one `dashboardTheme` |
| **Steps** | 1. `POST` mutation `insertUpdateThemeSetting` create theme setting with `themeType=chatbotTheme`. 2. `POST` mutation `insertUpdateThemeSetting` create theme setting with `themeType=dashboardTheme`. 3. `POST` query `themeSettingList(themeType: "chatbotTheme")` → verify only `chatbotTheme` entries returned. 4. `POST` query `themeSettingList(themeType: "dashboardTheme")` → verify only `dashboardTheme` entries returned. 5. Cleanup both theme settings. |
| **Expected behavior** | Type filter returns correct subsets; `chatbotTheme` filter excludes `dashboardTheme` and vice versa; `total` field reflects filtered count |
| **Validation points** | chatbot_theme_filter, dashboard_theme_filter, filter_exclusion |
| **Cross-system checks** | Filter result counts correct; existing 15 `chatbotTheme` entries visible in `chatbotTheme` filter |

## 8. Failure and Resilience Scenarios

| Scenario | Injected fault | Expected behavior |
|---|---|---|
| missing gateway | stop gateway before live execution | HTTP client connection fails; script exits with connection error message |
| invalid credentials | bad `TOKEN_USERNAME` / `TOKEN_PASSWORD` | `/auth/token` returns 401; token request fails; no tests execute |
| expired JWT | use expired token | Gateway returns 401 on GraphQL POST; client detects and re-authenticates (or exits with auth error) |
| missing_data | `POST` query unknown `theme_uuid` / `setting_uuid` | Resolver returns `null`; HTTP 200 with `{"data": {...: null}}`; no exception surfaces to HTTP client |
| invalid_data | `POST` mutation `insertUpdateSetting` with malformed `setting` JSON | GraphQL validation error; HTTP 200 with `errors` array; no partial data persisted |
| api_failures | Repository `insert_update` raises mid-commit | Transaction rolls back; `session.rollback()` called by `dispatch_graphql` error handler; HTTP 500 or GraphQL error envelope returned |
| database_failures | PostgreSQL connection drop mid-query | `pool_pre_ping=True` detects; retry or graceful error; no silent corruption; HTTP 500 with error message |
| authentication_failures | AWS credentials missing in DynamoDB mode | `Config.initialize` raises at gateway startup; gateway fails to start with explicit error |
| service_outages | DynamoDB table missing / PostgreSQL schema not provisioned | `initialize_tables` raises at gateway startup; gateway fails to start |
| cache_failures | `method_cache` miss/stale | Safe fallback to fresh query; no HTTP-level error |
| gateway_graphql_error | GraphQL query syntax error | Gateway returns HTTP 200 with `{"errors": [...]}` array; no HTTP 500 |
| wrong_part_id | `Part-Id` header missing or malformed | Gateway raises `ValueError` for missing `endpoint_id` or `part_id`; HTTP 500 or 400 with error message |
| json_camel_case_type_mismatch | Variable `$setting` declared as `JSONCamelCase` (nullable) but mutation argument is `JSONCamelCase!` (non-null required) | GraphQL validation error: "Variable '$setting' of type 'JSONCamelCase' used in position expecting type 'JSONCamelCase!'"; test script must declare variables with `!` suffix for required fields |
| json_snake_case_string_coercion | `JSONSnakeCase` serializes numeric values as strings | Assertions on `setting` field values must tolerate string coercion (e.g., `3` stored as `"3"`) |

## 9. Data Reconciliation Checks

| Check | Rule | Tolerance |
|---|---|---|
| Referential integrity | No orphaned theme settings or settings; all entities resolvable by UUID within their tenant | 0 |
| Count consistency | Entities created == entities persisted (per type) | 0 |
| Cache freshness | Post-mutation query returns updated field values (no stale reads) | 0 mismatches |
| Timestamp drift | `updated_at` advances on every successful mutation | 0 (must strictly increase) |
| Audit completeness | Every `insert_update` sets `updated_by` and `updated_at` | 0 missing |
| RLS enforcement | Cross-tenant query returns `null` via gateway HTTP | 0 cross-tenant reads |
| HTTP response structure | Every gateway GraphQL response has valid JSON `{data, errors}` envelope | 0 malformed |
| Auth token validity | All GraphQL POST requests carry valid `Authorization: *** header | 0 missing |
| JSONCamelCase structure | `theme_setting.setting` preserves camelCase key names | 0 key name violations |
| JSONSnakeCase structure | `setting.setting` preserves snake_case key names | 0 key name violations |

## 10. Entry and Exit Criteria

**Entry criteria (testing may begin when):**

- SOP is approved.
- Local gateway is running and reachable.
- `setting_core_engine` is loaded into gateway (verified via `ping` query).
- `.env` names are configured (`GATEWAY_BASE_URL`, `TOKEN_USERNAME`, `TOKEN_PASSWORD`, `endpoint_id`, `part_id`).
- Backend schema provisioned: `alembic upgrade head` (PostgreSQL) or `initialize_tables` (DynamoDB) at gateway startup.
- Authentication succeeds (`/auth/token` returns JWT).
- `ping` query returns valid greeting via gateway HTTP.

**Exit criteria (certification may be issued when):**

- All P0 and P1 scenarios pass (INT-HTTP-000, INT-HTTP-001, INT-HTTP-002, INT-HTTP-003, INT-HTTP-004).
- Coverage ≥ 80% of scenarios in Section 7 executed (not skipped).
- No unexpected error responses remain (HTTP 4xx/5xx or GraphQL `errors` arrays).
- Any defects or data-contract issues found during execution have been fixed and retested.
- The final full dependency-ordered live suite has passed after the last fix.
- Per-call function results are exported to `docs/`.
- Any expected live no-op behavior is explicitly documented.
- Open environment warnings are listed as non-blocking or resolved.

## 11. CI Trigger and Cadence

| Trigger | Scope run | Required to pass |
|---|---|---|
| Manual local validation | full live suite via `run_http_integration.py` | yes for certification |
| Pre-release | full live suite plus report export (`--export`) | yes |
| Pull request | INT-HTTP-000, INT-HTTP-001, INT-HTTP-003 (smoke subset) | yes — blocks merge |
| Nightly | full suite against isolated test tenant | report only (non-blocking) |
| Gateway transport change | full live suite plus schema introspection verification | yes |
| Backend switch | full live suite under both `DB_BACKEND` values (restart gateway between runs) | yes |

## 12. Reporting and Certification Expectations

### 12.1 Report Format and Location

- **Report format:** Markdown.
- **Report artifact:** `docs/test_results/http_integration_certification_report.md` (default export path from `run_http_integration.py --export`).
- **Call log artifact:** `docs/test_results/live_call_log_http.json` (per-call JSON log).
- **Required certification decision:** `Integration Certified`, `Ready for UAT`, `Ready for Production`, `Ready with Conditions`, or `Not Ready`.
- **Distribution:** `bibow` (test owner + release manager).

### 12.2 Required Report Sections

1. **Header metadata** — generated-at, project, domain, environment, endpoint, partition, SOP reference, pass/fail/skipped/blocked counts, certification status.
2. **Executive Summary** — 3-6 sentences: what was certified, against which environment, headline result, blocking issues, certification decision.
3. **Scope** — in scope, out of scope, phases executed, phases skipped (with reason).
4. **Dependency Readiness** — table with Available / Configured / Initialized / Operational per dependency.
5. **Scenario Results** — table: scenario ID, name, priority, result.
6. **Function Results** — one block per call (see Section 12.3 below).
7. **End-to-End Workflow Validation** — table: workflow, steps executed, validation points, result.
8. **Coverage Analysis** — table: area, covered, total, %, notes.
9. **Certification Decision** — status, rationale, conditions, evidence sources.
10. **Sign-off** — role, name, date, decision.

### 12.3 Function Results — Per-Call Recording Format

> Every GraphQL HTTP POST and auth call executed during the certification run must be recorded as a separate block in the Function Results section, **in execution order**.

Each call block must contain:

| Field | Required | Description |
|---|---|---|
| **Number** | yes | Sequential call number (1, 2, 3, ...) |
| **Group** | yes | Logical group: `Tests` |
| **Method** | yes | The exact method invoked (e.g. `POST /auth/token`, `POST /{endpoint_id}/setting_core_graphql`) |
| **Short description** | yes | One-line summary of what the call does |
| **Status** | yes | `pass`, `fail`, `error`, `skipped`, or `blocked` |
| **Elapsed** | yes | Duration in milliseconds |
| **Scenario ID** | yes | SOP scenario reference (e.g. `INT-HTTP-001`) |
| **Arguments** | yes | Exact input arguments as JSON (HTTP headers, GraphQL query document, variables) |
| **Output** | yes | Returned output as JSON (HTTP status, GraphQL response payload). Truncate oversized payloads with `... (truncated)` marker. |
| **Expected** | on failure only | Expected shape or value when status is `fail` or `error` |
| **Error/diff** | on failure only | Error message, status code, or expected-vs-actual diff |

### 12.4 Minimum Certification Output

The report must include these minimum sections whenever certifying readiness:

- Scope tested
- Dependencies validated, provisioned, configured, initialized
- Execution order used
- Tests run with pass, fail, skipped counts
- Per-call Function Results: input arguments and output for every call
- Final certification status

## 13. Comparison with Companion SOP (Direct In-Process Transport)

| Aspect | Companion SOP (`integration_scenarios_sop.md`) | This SOP (`integration_scenarios_sop_http.md`) |
|---|---|---|
| Test script | `run_live_integration.py` + `test_postgresql_integration.py` (pytest) | `run_http_integration.py` (HTTP `requests`) |
| Transport | direct in-process `SettingCoreEngine.execute()` | HTTP POST to gateway `/{endpoint_id}/setting_core_graphql` |
| Gateway involved | no | yes (`silvaengine_gateway` dispatch) |
| Auth | none (in-process) | JWT Bearer token from `POST /auth/token` |
| Tenant routing | `partition_key` in params context | `Part-Id` request header → gateway builds `partition_key` |
| Backend selection | `DB_BACKEND` per `Config.initialize` call | `DB_BACKEND` at gateway startup; restart to switch |
| Execution model | synchronous (pytest) | synchronous (`requests`) |
| Report artifact | `docs/test_results/` (pytest reports) | `docs/test_results/http_integration_certification_report.md` |
| Additional validation | repository dispatch, adoption guard | HTTP transport layer, gateway dispatch, JWT auth, `Part-Id` routing, HTTP status codes |
| RLS enforcement | `set_rls_context` called directly | `set_rls_context` called by `dispatch_graphql` from `Part-Id` context |
| Session lifecycle | test handles `db_session.remove()` cleanup | `dispatch_graphql` handles `rollback()` + `remove()` automatically per request |
| JSONCamelCase/JSONSnakeCase | tested in-process | tested over HTTP; variables must use `!` suffix for required JSON fields; numeric values may be string-coerced |

## 14. Sign-off

| Role | Name | Date | Decision |
|---|---|---|---|
| Test owner | `bibow` | `<pending>` | `<pending>` |
| Release manager | `<pending>` | `<pending>` | `<pending>` |
| DB owner (PostgreSQL) | `<pending>` | `<pending>` | `<pending>` |

---

## Pending Confirmation Items

Before any test execution begins, the following placeholders need
explicit decisions:

1. **SOP owner / contact** (Section 1): confirm `bibow` as owner.
2. **Credential source confirmation** (Section 3): confirm `.env` + `GATEWAY_BASE_URL` / `TOKEN_*` as the approved secret sources.
3. **Dependency owners** (Section 4): who owns DynamoDB, PostgreSQL, and each library dependency for readiness sign-off?
4. **Provisioning policy** (Section 3): confirm auto-provisioning of the disposable PostgreSQL schema is allowed in the target environment.
5. **CI cadence** (Section 11): confirm the PR-block / nightly-report / pre-release-block split.
6. **Distribution list** (Section 12): who receives the certification report?
7. **Sign-off roles** (Section 14): names for test owner, release manager, DB owner.

Once these are confirmed, the SOP status moves from `draft` to `approved`
and test execution may proceed.