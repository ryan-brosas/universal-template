<!-- capsule-v2 -->
# ToolGuard Runtime — admin-authored guard code executed around every tool call, transparent until a guard applies

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** When does runtime policy enforcement block a tool call, when is it transparent, and which failure modes must fail closed?

## The four-block ladder inside guard_tool_call
**Path/Symbol:** `src/cuga/backend/cuga_graph/policy/tool_guard/tool_guard_runtime.py` (`ToolGuardRuntime.initialize` :72-125 storage connect fails ⇒ RuntimeError, `_register_policy_guards` :180-221 invalid code ⇒ `invalid_tool_guards`, `_build_tool_guard_module` :498-521 umbrella synthesis, `_extract_guard_function_name` :578-593 requires `async def guard_*`, `guard_tool_call` :761-874).

**Signature:** `async guard_tool_call(app_name: str, function_name: str, arguments: Dict[str, Any]) -> Optional[str]` — returns an error string (block) or None (allow).

**Data Shape:** Guards come from ToolGuide policies' `tool_guards: {tool_name: {violating_examples, compliance_examples, policy_code}}` with `guards_enabled` flag. Registration builds `tool_to_guards: Dict[tool_name, List[ToolGuide]]` and `invalid_tool_guards`. Per-app in-memory runtimes are built lazily from domain files under `{cuga_folder}/toolguard/domain/{app}/({app}_types.py, i_{app}.py, {app}_impl.py)` with exact-then-fuzzy (`"crm" → "crm_demo"` substring) directory matching.

### Decisive source
```python
# tool_guard_runtime.py:862-871 — internal errors are violations, verbatim:
except PolicyViolationException as e:
    ...
    return error
except Exception as e:
    logger.error(...)
    # Fail closed: treat internal guard errors as a violation so a buggy
    # or malformed guard cannot silently bypass policy enforcement.
    return (
        f"Internal guard error for '{function_name}': {e}. "
        "Tool call blocked as a safety precaution."
    )
```
The full decision ladder (:778-830): not initialized ⇒ None (transparent); invalid declared guard code for this tool+app ⇒ BLOCK; no registered guards ⇒ None; guards exist but none match after `target_apps` filtering ⇒ None + warning ("Tool call will proceed unguarded"); applicable guards but runtime/domain can't load ⇒ BLOCK; guard raises PolicyViolationException ⇒ BLOCK with message; any other guard exception ⇒ BLOCK; parameter literally named `args` ⇒ BLOCK (:841-850 — collides with the injected `SimpleNamespace` args namespace).

**Flow:** initialize connects storage (enabled-but-failed ⇒ RuntimeError, service refuses to start without enforcement) and registers only policies whose `policy_code` contains a parseable `async def guard_*` → per-app umbrella module generated: each policy's code inlined, its guard aliased `_guard_validate_{i}`, one umbrella `async def guard_{tool}_{hash}(api, args)` runs all validators, collecting `[PolicyName] message` violations and raising joined PolicyViolationException → wrapper calls this before every tool execution; arguments are type-cast through the tool's pydantic `args_schema` first (:711-759).

**Invariant:** Transparency vs enforcement is decided ONLY by "does an applicable guard exist for this app/tool". No applicable guard ⇒ never blocks (the wrapper is invisible); applicable guard present ⇒ every failure mode blocks. Porters who make the error path fail-open turn any bug into a policy bypass; porters who make the no-guard path block break every unguarded integration.

**Probe:** `tests/unit/test_toolguard_provider.py:236 test_toolguard_runtime_blocks_on_internal_guard_error`, `:254 ..._blocks_when_runtime_unavailable_for_applicable_guard`, `:276 ..._blocks_invalid_declared_policy_code` (also asserts the tool left `tool_to_guards` and landed in `invalid_tool_guards`), `:300 ..._blocks_args_parameter_collision` (asserts zero delegate calls), `:319 ..._type_casts_with_tool_args_schema` (string "4" arrives as int).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "guard_tool_call fail closed invalid_tool_guards", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the existence-of-applicable-guard transparency rule and the four-block fail-closed ladder, plus args-schema type casting before validation. Adapt the toolguard library dependency (in-memory FileTwin runtimes) to your sandbox story; the trust model doc warns policy_code runs with backend-service privileges — sandbox it or keep it admin-only.
