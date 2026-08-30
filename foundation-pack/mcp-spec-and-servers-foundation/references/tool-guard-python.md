<!-- capsule-v2 -->
# Low-level Python server patterns — pydantic-schema tools, McpError code mapping, and consent/hardening gates (fetch, git, time)

**Source:** modelcontextprotocol/servers MIT `main@76d64c8`; Codebase Memory `servers`. **Question:** How do the Python reference servers structure tool handlers, map failures to JSON-RPC codes, and gate dangerous operations?

## Pydantic model ⇒ inputSchema; domain errors as McpError(INVALID_PARAMS|INTERNAL_ERROR); consent before side effects
**Path/Symbol:** `src/fetch/src/mcp_server_fetch/server.py` (`Fetch(BaseModel)` :151–178 with `Annotated[..., Field(gt=0, lt=1_000_000)]` bounds; `serve()` :181–288 — `@server.list_tools` returning `Tool(name, description, inputSchema=Fetch.model_json_schema())`, `@server.call_tool` :223–255 validating `Fetch(**arguments)` with `except ValueError → McpError(INVALID_PARAMS)`; robots gate `check_may_autonomously_fetch_url` :66–108 raising INTERNAL_ERROR with actionable copy; truncation loop :240–254 appending "call again with start_index=N"); `src/git/src/mcp_server_git/server.py` (`validate_repo_path` :252–270 resolve-then-relative_to; flag-injection guard `git_branch` :273–278 rejecting `-`-prefixed contains/not_contains; roots+CLI repo union :462–485; single dispatching `call_tool` :487–598); `src/time/src/mcp_server_time/server.py:53–57 get_zoneinfo → McpError(INVALID_PARAMS, "Invalid timezone: ...")`.

### Decisive source
```python
# fetch/server.py:223-235 — validation + consent ordering
@server.call_tool()
async def call_tool(name, arguments: dict) -> list[TextContent]:
    try:
        args = Fetch(**arguments)
    except ValueError as e:
        raise McpError(ErrorData(code=INVALID_PARAMS, message=str(e)))
    url = str(args.url)
    if not url:
        raise McpError(ErrorData(code=INVALID_PARAMS, message="URL is required"))
    if not ignore_robots_txt:
        await check_may_autonomously_fetch_url(url, user_agent_autonomous, proxy_url)
```
```python
# git/server.py:273-278 — defense in depth against CLI flag injection
def git_branch(repo, branch_type, contains=None, not_contains=None):
    if contains and contains.startswith("-"):
        raise BadName(f"Invalid contains value: '{contains}' - cannot start with '-'")
    if not_contains and not_contains.startswith("-"):
        raise BadName(...)
```
Robots gate details (:87–108): 401/403 on robots.txt ⇒ refuse autonomously; other 4xx ⇒ treat as allowed; denial raises INTERNAL_ERROR whose message embeds `<useragent>/<url>/<robots>` and instructs the assistant to offer the manual-fetch prompt. Truncation contract (:241–254): `start_index >= len` or empty slice ⇒ `<error>No more content available.</error>`; full-length slice with remainder ⇒ append the exact next `start_index` so the LLM can continue. Git path validation (:254–270): resolve both sides then `.relative_to()` — ValueError ⇒ outside; optional restriction (None = unrestricted); per-tool annotations set readOnlyHint/destructiveHint truthfully (status/diff/log read-only vs commit/add/reset destructive).

**Flow:** arguments dict → pydantic construct (schema errors = INVALID_PARAMS) → consent/validation gates → perform → TextContent result. Time shows the minimal variant: one enum of two tools, tz parse failure mapped to INVALID_PARAMS, everything else pure computation.

**Invariant:** argument-shape failures are client errors (-32602-class INVALID_PARAMS), environment/remote failures are INTERNAL_ERROR with human-actionable messages; consent gates run BEFORE any network side effect; user-controlled strings that reach a subprocess argv must be rejected when they begin with `-`.

**Probe:** `src/fetch/tests/test_server.py::TestGetRobotsTxtUrl.test_simple_url..test_http_url` (:19–50 pin URL→robots.txt derivation), `TestExtractContentFromHtml` (:53+); `src/git/tests/test_server.py::test_git_add_rejects_path_traversal` (:112 — CVE-2026-27735 regression: relative escape never staged), `::test_git_add_rejects_absolute_path_outside` (:127), `test_git_branch_contains/not_contains` (:61/:75); `src/time/test/time_server_test.py::test_get_current_time_with_invalid_timezone` (:85), `test_get_local_tz_*` (:465+).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "servers", query: "check_may_autonomously_fetch_url validate_repo_path git_branch flag injection", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt pydantic-model-as-inputSchema, strict INVALID_PARAMS-vs-INTERNAL_ERROR mapping, pre-side-effect consent gates with self-explaining errors, continuation-index pagination for truncated payloads, resolve-and-relative_to path confinement, and argv dash-rejection; adapt tool catalogs, user agents, and message copy; omit markdownify/readability internals and GitPython specifics unless porting those servers wholesale.
