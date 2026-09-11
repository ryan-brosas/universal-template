<!-- capsule-v2 -->
# Tool metadata stash — where must per-tool prompt metadata live so StructuredTool copies, deep-copies, and wrappers can't lose it?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** Response schemas and param constraints are NOT pydantic fields of the tool — how do they travel from tool construction to the prompt builder?

## Function-attribute stashing at creation time
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_lite/providers/registry.py:284-298` (`create_tool_from_api_dict`); producer-twin `providers/combined.py:184-193` (`create_tool_from_tracker`); consumer `prompt_utils.py:291-298,313-319` (`is_weak_schema_tool`, `get_tool_docs`); payload serializer `prompt_utils.py:397-405` (`_build_shortlister_payload`).
**Signature:** attributes set on BOTH callables: `tool.func._response_schemas`, `tool.coroutine._response_schemas`, `tool.func._param_constraints`, `tool.coroutine._param_constraints`; identity metadata on all three: `target._operation_id`, `target._app_name` for `(tool.func, tool.coroutine, tool)`.
**Data Shape:** `_response_schemas: dict` (`success`/`failure` JSON schemas + optional `_synthetic_placeholder` sentinel); `_param_constraints: dict[name, list]`.

### Decisive source
```python
# registry.py:284-292 — guard-with-if (never clobber pre-existing values)
if not hasattr(tool.func, "_response_schemas"):
    tool.func._response_schemas = response_schemas
if not hasattr(tool.coroutine, "_response_schemas"):
    tool.coroutine._response_schemas = response_schemas

# prompt_utils.py:397-405 — the shortlister payload MUST re-expose them,
# because tool.model_dump() drops plain function attributes:
if hasattr(tool, 'func'):
    if hasattr(tool.func, '_response_schemas'):
        tool_dict['_response_schemas'] = tool.func._response_schemas
    if hasattr(tool.func, '_param_constraints'):
        tool_dict['_param_constraints'] = tool.func._param_constraints
```
Per coderabbit on cuga-agent#203 (:373-376): "keeping a single payload builder prevents the two callers from drifting — both must include ``args_schema``, ``_response_schemas``, and ``_param_constraints`` for the LLM to rank tools consistently."

**Flow:** provider builds InputModel + extracts constraints/schemas → creates `StructuredTool.from_function(func=..., coroutine=...)` → stashes everything as function attributes guarded by `hasattr` → downstream consumers read them back off `tool.func` for prompt docs, weak-schema detection, and shortlister payloads; tracker-side tools set constraints only (schemas unknown ⇒ weak-schema path).
**Invariant:** these keys live on `tool.func`/`tool.coroutine`, NOT on the StructuredTool itself — a porter who puts them in the pydantic model loses them on `.model_dump()` round-trips and breaks ranking consistency; conversely a porter who forgets to re-expose them in serialized payloads silently degrades the ranker's inputs. The combined-provider twin sets ONLY `_param_constraints` (no schemas) — consumers must tolerate absence.
**Probe:** pinned transitively by `tests/test_prompt_utils_weak_schema.py` fixtures which construct tools via `SimpleNamespace(func=SimpleNamespace(_response_schemas=...))` — proving consumers read the attribute contract, not the class. No direct test asserts the stash itself (coverage caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "_response_schemas _param_constraints create_tool_from_api_dict", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt function-attribute stashing with hasattr-guards when you need non-pydantic metadata to survive LangChain tool plumbing, AND adopt the explicit re-exposure rule for any serialization of tools into prompts/LLM payloads; adapt attribute names; omit the operation_id/_app_name trio if your tracking layer doesn't need per-call provenance. Coverage caveat: consumer side directly tested; producer side source-read verified.
