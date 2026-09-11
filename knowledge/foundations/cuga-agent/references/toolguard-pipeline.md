<!-- capsule-v2 -->
# ToolGuard generation pipeline — how does a server drive examples→codegen→persist→invalidate end to end?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How do you orchestrate guard generation over many policies/tools so partial failure is visible and the runtime never serves stale guards?

## Server pipeline: per-tool two-phase generation with per-tool error isolation
**Path/Symbol:** `src/cuga/backend/server/tool_guard_generation.py` (`_concrete_target_tools` :33-37, `generate_tool_guards_for_policy` :40-91, `_batch_status` :94-110, `generate_tool_guards_for_policies` :113-161); SDK write path `src/cuga/sdk.py:update_tool_guard` (:734-820) + `generate_tool_guard_examples`/`generate_tool_guard_code` (:1554-1728).
**Signature:** `await generate_tool_guards_for_policy(*, policy_system, policy_id, generation_agent) -> {"status", "policy_id", "results"}`; `update_tool_guard(policy_id, tool_guards: Dict[tool, {violating_examples|compliance_examples|policy_code}]) -> policy_id`.
**Data Shape:** A dedicated generation agent is built with `auto_load_policies=False, filesystem_sync=False` (:23-30) so batch writes don't re-trigger folder sync or lazy loads mid-run. Per-tool result rows `{tool, status: ok|error}`; batch status ∈ `ok|partial|error`.

### Decisive source
```python
# tool_guard_generation.py:57-83 — exact per-tool phase order
for tool_name in target_tools:
    try:
        (violating_examples, compliance_examples) = await generation_agent.policies.generate_tool_guard_examples(...)
        await generation_agent.policies.update_tool_guard(policy_id=policy_id, tool_guards={
            tool_name: {"violating_examples": violating_examples, "compliance_examples": compliance_examples}})
        policy_code = await generation_agent.policies.generate_tool_guard_code(...)
        await generation_agent.policies.update_tool_guard(policy_id=policy_id,
            tool_guards={tool_name: {"policy_code": policy_code}})
        results.append({"tool": tool_name, "status": "ok"})
    except Exception:
        logger.exception("ToolGuard generation failed for tool %s in policy %s", ...)
        results.append({"tool": tool_name, "status": "error", ...})

# sdk.py:update_tool_guard tail — merge, reload, mirror, invalidate
tool_guards_obj = merge_tool_guards(existing_policy.tool_guards, tool_guards)
...
await policy_system.storage.update_policy(updated_policy)
await policy_system.initialize()  # Reload policies
if self._fs_sync:
    self._fs_sync.save_policy_to_file(updated_policy)
self._invalidate_toolguard_runtime()
```

**Flow:** validate eligibility once (exists / is ToolGuide / enabled / concrete target_tools — `"*"` raises "Select specific target tools") → per tool: generate examples → persist them via MERGE (`merge_tool_guards`, never whole-object overwrite) → generate code (reads examples back from storage) → persist code → after every update: reload the policy system into the singleton, mirror to `.cuga/<subfolder>/<id>.md` if sync on, and `_invalidate_toolguard_runtime()` so wrapped providers rebuild instead of serving stale guards → roll up statuses; top-level = ok iff ANY tool succeeded.
**Invariant:** Examples and code are persisted through STORAGE between phases (never held only in memory), merged per-tool-key rather than replacing `tool_guards`, and every mutation ends with runtime invalidation — this is what makes the freshly generated guard code actually take effect at the provider boundary (pairs with `provider-decorator` + `toolguard-manager` capsules). Per-tool try/except keeps one bad LLM call from killing the batch.
**Probe:** No direct test for the server module (coverage caveat); behavior pinned indirectly by `tests/unit/test_toolguard_provider.py` invalidation expectations and `policy/tests/test_utils.py` for the JSON import/export path (`validate_output_formatter` quartet). The merge helper itself has a unit test (`test_toolguard_provider.py:412` region, pass-1 record).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "generate_tool_guards_for_policies", limit: 5 });
```

## Verdict
Adopt the phase order (examples → persist-merged → codegen → persist), the post-update triple (reload singleton + FS mirror + runtime invalidation), and per-tool error isolation with rolled-up status. Adapt agent-construction flags and status vocabulary to your host. Omit the FastAPI route surface.
