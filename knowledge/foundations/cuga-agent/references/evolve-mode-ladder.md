<!-- capsule-v2 -->
# Evolve mode ladder — how does an optional MCP memory integration resolve registry-vs-direct transport and stay 100% non-fatal?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** When an enhancement service (guidelines/user-facts) may or may not be registered, how do you route calls and bound them without ever crashing the agent?

## EvolveIntegration._call_tool + fail-open composition
**Path/Symbol:** `src/cuga/backend/evolve/integration.py:38-55,219-331` (`_get_mode`, `is_enabled`, `_call_tool`, `_call_tool_via_registry`, `_call_tool_direct`); prompt-side composition `src/cuga/backend/evolve/memory.py:23-113` (`build_evolve_special_instructions_extension`); call sites: `adapter/prepare_node.py:514-520`, `cuga_lite_node.py:403-429`.
**Signature:** `async _call_tool(cls, tool_name: str, args: dict)`; modes = `auto | registry | direct` (invalid ⇒ auto).
**Data Shape:** registry path posts `{app_name, function_name: f"{app}_{tool}", args}` to `/functions/call`; direct path uses FastMCP `SSETransport` with `asyncio.wait_for(timeout)`.

### Decisive source
```python
if mode in {"auto", "registry"} and registry_enabled:
    try:
        return await cls._call_tool_via_registry(tool_name, args)
    except Exception as e:
        if mode == "registry":
            raise                      # explicit mode ⇒ surface the failure
        logger.debug(f"...falling back to direct SSE: {e}")   # auto ⇒ fall through

if mode in {"auto", "direct"}:
    return await cls._call_tool_direct(tool_name, args)
```
Prompt-composition side (memory.py:51-62):
```python
evolve_guidelines = await asyncio.wait_for(EvolveIntegration.get_guidelines(...), timeout=timeout)
except Exception:
    logger.warning("Evolve: get_guidelines timed out or failed; continuing without guidelines")
    evolve_guidelines = None
```

**Flow:** enabled gate (`enabled` ∧ ¬(lite_mode_only ∧ ¬lite_mode)) → per-call mode resolution → registry attempt only if registry is on AND the app is actually present (`_registry_has_app` check raises a clean RuntimeError otherwise) → auto falls back to direct SSE → every public method wraps everything in try/except-warning-return-None. The prompt extension composes guidelines + user-preferences sections under ONE timeout each; the user-fact WRITE is fire-and-forget (`asyncio.create_task` + done-callback that logs exceptions).
**Invariant:** module docstring is the contract: "All operations are non-fatal: errors are logged as warnings and never crash the agent" — an enhancement must never degrade the run it decorates; explicit `mode=registry` is the ONE place errors propagate (user asked for exactly that transport); reads are timeout-bounded, writes are detached tasks.
**Probe:** `src/cuga/backend/evolve/tests/test_integration.py`: enable-gate matrix :24-48; disabled short-circuits :105-123/:143; error⇒None (:172); payload passthrough (:151,:184). Timeout-bounded composition + fire-and-forget write verified by source read (coverage caveat: no dedicated test for memory.py).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "EvolveIntegration _call_tool _registry_has_app get_guidelines", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the auto/registry/direct ladder with explicit-mode-propagates semantics for any optional backend with two transports; adopt read-bounded/write-detached discipline when decorating prompts with external data; adapt tool names/timeouts; omit the FastMCP leg if you only speak one transport. Direct tests pin gating + failure returns; fallback ordering source-pinned.
