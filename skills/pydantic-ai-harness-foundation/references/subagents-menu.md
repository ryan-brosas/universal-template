<!-- capsule-v2 -->
# SubAgents model menu — a named delegate tool with per-delegate run controls and a validated model-restriction ladder

**Source:** pydantic-ai-harness (MIT) `main@c79fabc58fd3bd587dcc27f9e7d9de179d748cf0`; Codebase Memory `pydantic-ai-harness`. **Question:** how does a harness expose child agents as a single delegate tool, route delegations across a named model menu, and contain child errors without breaking parent control-flow?

## SubAgents capability + SubAgentToolset
**Path/Symbol:** `pydantic_ai_harness/subagents/_capability.py` (340L), `_toolset.py` (399L, `SubAgentToolset`), `_models.py` (84L, `ModelOption`, `as_option`, `model_label`, `validate_restriction`), `_disk.py`, `_effort.py`.
**Signature:** `SubAgents(agents=[SubAgent(agent, name=None, description=None, ...)], models={'fast': ..., 'deep': ModelOption(...)}, ...)`; delegate tool `run_subagent(name, model, task)`.
**Data Shape:** `ModelOption(model, description=None, settings=None)` — a menu entry as a model plus how it should run. `as_option` normalizes a bare model reference; `model_label` names a `Model` as `<system>:<model_name>`. Per-delegate `SubAgent.models` restriction validated against the configured menu.

### Decisive source
```python
# validate_restriction: an empty restriction raises ValueError ("Leave `models`
# unset to allow every configured model"); unknown keys raise with the
# configured options listed.
# _ALWAYS_PROPAGATE = (CallDeferred, ApprovalRequired, SkipModelRequest,
#   SkipToolValidation, SkipToolExecution, UserError)
# Signals that must always reach the parent run even when a delegate has
# `contain_errors` on. Containing the first five would break the agent graph
# (deferred/approval/skip control-flow); a UserError is a setup bug no retry
# can fix. Cancellation (a BaseException) is out of `except Exception`'s reach;
# a shared UsageLimitExceeded has its own clause.
```

**Flow:** parent model calls `run_subagent` → route to the named `ModelOption` (settings merge over the sub-agent's own `model_settings`) → run child → contain child errors per `contain_errors` except `_ALWAYS_PROPAGATE` → return result.
**Invariant:** the always-propagate set is a hard contract — containing deferred/approval/skip signals would break the agent graph; a `UserError` is never masked into a retry.
**Probe:** `tests/subagents/test_subagents.py` pins routing, model-restriction validation, error containment, and the always-propagate set.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-ai-harness", query: "SubAgents SubAgentToolset ModelOption validate_restriction _ALWAYS_PROPAGATE", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the model-menu routing, per-delegate restrictions, and the always-propagate error contract; adapt the delegate tool signature; omit host-specific sub-agent run controls.
