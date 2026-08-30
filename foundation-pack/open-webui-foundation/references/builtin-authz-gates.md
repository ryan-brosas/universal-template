<!-- capsule-v2 -->
# Built-in tool authz gates — how do you guarantee a legacy second execution path enforces identical authorization to the primary path?

**Source:** open-webui "Open WebUI License" (BSD-3-Clause base + branding condition; citations-only) `main@01f4282f1ffe0d6212f58d3afbeae21fffd0c4be`; Codebase Memory `open-webui`. **Question:** When tool execution has two entrances (native function-calling and an XML-tag fallback), how do I stop the fallback from becoming an authz bypass?

## The documented mirror gate
**Path/Symbol:** `backend/open_webui/utils/middleware.py` `DETECT_CODE_INTERPRETER` (4121-4142) mirroring `backend/open_webui/utils/tools.py:get_builtin_tools` (520-802).
**Signature:** five-factor boolean: `bool(features.get('code_interpreter')) and builtin_tools_meta.get('code_interpreter', True) and await Config.get('code_interpreter.enable') and model_capabilities.get('code_interpreter', True) and (admin or has_permission(user.id, 'features.code_interpreter', user.permissions))`.
**Data Shape:** factors come from three layers: request `metadata.features`, model info (`meta.capabilities`, `meta.builtinTools`), global DB config + per-user permissions.

### Decisive source
```python
# Mirror the five gates from utils/tools.py get_builtin_tools so the
# legacy XML-tag path enforces the same authz as native FC.
...
DETECT_CODE_INTERPRETER = (
    bool(features.get('code_interpreter'))
    and builtin_tools_meta.get('code_interpreter', True)
    and await Config.get('code_interpreter.enable')
    and model_capabilities.get('code_interpreter', True)
    and (
        getattr(user, 'role', None) == 'admin'
        or await has_permission(
            getattr(user, 'id', ''),
            'features.code_interpreter',
            await Config.get('user.permissions'),
        )
    )
)
```
(middleware.py 4124-4142)

**Flow:** the canonical gate lives in `get_builtin_tools`'s code-interpreter arm: `is_builtin_tool_enabled('code_interpreter') ∧ config['code_interpreter.enable'] ∧ get_model_capability('code_interpreter') ∧ features['code_interpreter'] ∧ has_user_permission('code_interpreter')` (admin short-circuits). The tag-scanner path cannot see that function, so it re-evaluates the same five factors inline before enabling XML-tag detection.
**Invariant:** both defaults are opt-out (`capabilities`/`builtinTools` default True) but the conjunction is still fail-closed because every factor must be independently true; admin bypass is role-based only. The invariant to port: **the comment is part of the contract** — the mirror exists to be found when one side changes.
**Probe:** no upstream tests exist at this pin (zero test files repo-wide — recorded block). Deterministic anchors: `grep -n "Mirror the five gates" backend/open_webui/utils/middleware.py` → 4124; `sed -n '4129,4142p' backend/open_webui/utils/middleware.py` reproduces the gate; `grep -n "MUTATING_MEMORY_TOOLS" backend/open_webui/utils/tools.py` → 767 (import) and 769 (strip).

## Adjacent gating facts in the canonical source
From `get_builtin_tools` direct read (utils/tools.py 520-802): subagent tools (`delegate_task`, `timer`) require category enable AND global `subagents.enable` AND NOT `request.state.internal` AND NOT `request.state.direct`; internal requests additionally have `MUTATING_MEMORY_TOOLS` stripped from the final list; `delegate_task`'s `background` parameter is popped from its spec (and from `required`) when `subagents.background_enabled` is false — capability removal at the schema level, not just runtime denial.
**Invariant (adjacent):** internal/direct callers get a *smaller* tool surface, never a larger one — trust level narrows capabilities instead of widening them.
**Probe (adjacent):** `grep -n "getattr(request.state, 'internal', False)" backend/open_webui/utils/tools.py` → 647 (exclusion arm) and 766 (strip arm).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "open-webui", query: "get_builtin_tools builtin tool enabled capability user permission", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the pattern: enumerate every authorization factor of the primary path, re-evaluate them inline at any secondary entrance, and mark the mirror with a comment naming what it mirrors. Adopt the narrower-trust rule for internal callers and spec-level parameter stripping over runtime checks. Adapt the specific factor set (features/capabilities/builtinTools/user.permissions layering) to your own config planes. Omit open-webui's tool catalog. Coverage caveat: both files graph-clean, no upstream tests; claims pinned by direct source reads at lines cited above.
