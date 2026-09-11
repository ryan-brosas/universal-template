<!-- capsule-v2 -->
# Dynamic system-prompt re-evaluation — refresh placeholder prompts in place, never re-emit

**Source:** pydantic-ai (MIT) `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** When a conversation continues across runs, how do dynamic (function-backed) system prompts get refreshed without duplicating system messages in history?

## UserPromptNode._reevaluate_dynamic_prompts
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/_agent_graph.py:UserPromptNode._reevaluate_dynamic_prompts` (707-732); runner registry `system_prompt_dynamic_functions` (519-521).
**Signature:** `async _reevaluate_dynamic_prompts(messages: list[ModelMessage], run_context: RunContext) -> None`.
**Data Shape:** map of `dynamic_ref → SystemPromptRunner`; matches `SystemPromptPart` parts whose `.dynamic_ref` is set.

### Decisive source
```python
if self.system_prompt_dynamic_functions:
    for msg in messages:
        if isinstance(msg, ModelRequest):
            for part in msg.parts:
                if isinstance(part, SystemPromptPart) and part.dynamic_ref:
                    if runner := self.system_prompt_dynamic_functions.get(part.dynamic_ref):
                        # placeholder string keeps the ref valid in FUTURE runs
                        updated = await runner.run(run_context)
                        part = SystemPromptPart(updated or '', dynamic_ref=part.dynamic_ref)
            ...
            # Replace message parts with reevaluated ones to prevent mutating parts list
            if reevaluated != msg.parts: msg.parts = reevaluated
```

**Flow:** on each run's UserPromptNode pass over the (cleaned) history → for every ModelRequest part carrying a `dynamic_ref`, look up the runner by ref → re-run it with the current RunContext → replace the part content while PRESERVING the ref.
**Invariant:** The `dynamic_ref` stays on the refreshed part — stripping it would make the prompt permanently static and un-refreshable in later runs. Replacement is whole-list (new list assigned back), not in-place part mutation. Only parts whose runner is registered are touched; unknown refs survive untouched. Static system prompts are never duplicated: they're emitted only into empty histories (see user-prompt-node-routing).
**Probe:** exercised via every multi-run agent test that uses `@agent.system_prompt` — e.g. `tests/test_agent.py` dynamic system-prompt suites around line 3814 (`capture_run_messages` runs).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "_reevaluate_dynamic_prompts SystemPromptPart dynamic_ref", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ref-preserving in-place refresh pattern (portable to any templated/ephemeral context injection); adapt the registry keying to your host's prompt-id scheme; omit the pydantic-ai SystemPromptRunner wrapper shape. Coverage clean.
