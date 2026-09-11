<!-- capsule-v2 -->
# ToolGuard Manager — how does CUGA generate guard code from a policy at build time?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How do you turn a ToolGuide policy into violating/compliance examples and executable guard code without corrupting the tool metadata the generation depends on?

## Build-time twin of the runtime ladder (`toolguard-runtime` capsule)
**Path/Symbol:** `src/cuga/backend/cuga_graph/policy/tool_guard/manager.py:ToolGuardManager` (`__init__` :35-76, `initialize` :78-104, `generate_examples` :360-422, `generate_guard_code` :424-539).
**Signature:** `ToolGuardManager(agent: CugaAgent)`; `await manager.initialize()`; `await manager.generate_examples(policy: ToolGuide, target_tool: str) -> Tuple[List[str], List[str]]`; `await manager.generate_guard_code(policy, target_tool, app_name: Optional[str] = None) -> str`.
**Data Shape:** Wraps the external `toolguard.buildtime` library (`generate_guard_examples`, `generate_guards_code`, `LangchainModelWrapper`, `langchain_tools_to_openapi`). Working dir `<cuga_folder>/toolguard/`; each call gets a unique `tmp_<uuid>` subdir removed in `finally` (`_temp_directory` :330-347). Constructor eagerly validates `tool_provider`, `cuga_folder`, `_model` with ValueError — fail-closed service start.

### Decisive source
```python
# initialize(): generation MUST use raw tools, not guarded wrappers (:87-95)
# Get raw LangChain tools from the provider when available. ToolGuard
# generation needs the original function annotations/metadata; guarded
# wrapper tools intentionally replace the callable and can lose return
# annotations such as `-> str`.
if hasattr(self.tool_provider, "get_all_raw_tools"):
    self.langchain_tools = await self.tool_provider.get_all_raw_tools()
else:
    self.langchain_tools = await self.tool_provider.get_all_tools()

# generate_guard_code(): hard ordering gate (:476-480)
if not violating_examples and not compliance_examples:
    raise ValueError(
        f"Policy for tool '{target_tool}' must have examples before generating guard code. "
        f"Call generate_examples() first to provide them in the policy's tool_guards."
    )
```

**Flow:** construct (validate deps, mkdir workdir) → `initialize()` once under `asyncio.Lock` (`_initialized` guard) → fetch RAW tools → build `tool→[app names]` index → convert to OpenAPI dict → enrich response schemas → per policy: `generate_examples(policy, tool)` (LLM writes violation/compliance examples via `ToolGuardSpec`) → persist examples into the policy's `tool_guards` (caller does this) → `generate_guard_code(policy, tool)` reads examples back out of `policy.tool_guards[target_tool]`, calls codegen, saves RuntimeDomain files (`app_types/app_api/app_api_impl` → `<workdir>/domain/`, :349-358), returns first `item_guard_file.content`.
**Invariant:** Generation consumes **raw** tools — guarded wrappers lose `-> str` return annotations, which degrades generated guards (they treat primitive responses as objects and extract nonexistent fields). And codegen refuses to run before examples exist: examples are persisted through storage between the two calls, so the policy object round-trips.
**Probe:** NO direct unit test exists for `ToolGuardManager` (`grep -rl ToolGuardManager src --include="test_*.py"` = empty) — behavior pinned by the runtime side consuming its output (`tests/unit/test_toolguard_provider.py`). Coverage caveat: port with extra manual verification.
**Response-schema enrichment** (`_enrich_response_schemas_from_annotations` :167-214): infers JSON schema from the original callable's `return` annotation (`func`/`coroutine`; unwrap Optional, map str/int/float/bool/list/dict); writes it into the OpenAPI operation's `responses.200.content.application/json.schema` ONLY if the existing schema has neither `type` nor `properties` (:210) — registry-provided rich schemas win over inferred ones.
**app_name discipline:** `_validate_app_name` (:235-262) rejects `/`, `\`, `..`, anything outside `[A-Za-z0-9_-]+` — path-traversal defense because app_name becomes a directory name; `_infer_app_name_from_tool` (:264-299) requires exactly ONE owning app, raises on ambiguity ("Pass app_name explicitly"), falls back to `tool.func._app_name` metadata.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "ToolGuardManager.generate_guard_code", limit: 5, fields: ["signature", "name", "file"] });
// → manager.py 424-539; also __init__ 35-76, initialize 78-104
```

## Verdict
Adopt the two-phase flow (examples → persist → codegen), the raw-tools requirement, annotation-driven response enrichment gated on placeholder schemas, and the app_name whitelist/inference rules. Adapt the `toolguard` library calls and OpenAPI conversion to your stack. Omit the demo-specific `CugaAgent` coupling. Caveat: no direct tests cover this class upstream — treat the runtime capsules' probes as indirect only.
