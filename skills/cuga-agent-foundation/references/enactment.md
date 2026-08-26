<!-- capsule-v2 -->
# Policy Enactment — one entry point that turns a match into either a graph Command or state metadata, without ever crashing the run

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How does a graph node ask "any policies apply?" and get back something it can act on, while guaranteeing a broken policy system can never take down the agent?

## check_and_enact: target inference + fail-open wrapper
**Path/Symbol:** `src/cuga/backend/cuga_graph/policy/enactment.py` (`check_and_enact` :36-233, `_merge_guide_metadata` :236-273, `_enact_policy_action` :276-329 dispatch, `inject_playbook_into_prompt` :521-555, `apply_tool_restrictions` :557-580).

**Signature:** `async check_and_enact(state, config=None, policy_types=None, adapter=None, metadata_key=None) -> tuple[Optional[Command], Optional[Dict[str, Any]]]`.

**Data Shape:** `(command, metadata)`; command is a LangGraph `Command` (only for BLOCK_INTENT today) whose `update` dict embeds the policy metadata under `metadata_key`; metadata merges into `state.cuga_lite_metadata` (or the adapter's key). Target is inferred from `policy_types`: contains OUTPUT_FORMATTER ⇒ `target="agent_response"`, stage OUTPUT; INTENT_GUARD/PLAYBOOK ⇒ `"intent"`/INPUT; None ⇒ defaults to `[INTENT_GUARD, PLAYBOOK]`.

### Decisive source
```python
# enactment.py:231-233 — the whole engine is wrapped:
except Exception as e:
    logger.warning(f"Policy check failed (continuing without policies): {e}", exc_info=True)
    return None, None
# Guides are additive and never overwrite a main policy (:129-131):
# ALWAYS apply Tool Guide policies ... regardless of whether a
# playbook/intent guard matched. Skip for OutputFormatter checks.
```
And the merge rule (:135-149): when both exist, main-policy keys (`policy_type`, `policy_id`, `policy_name`) are preserved and guide facts land under separate `guides` / `guide_policies` / `has_guides` keys.

**Flow:** infer target/stage → `PolicyConfigurable.from_config` → build context → `match_policy` → optional `agent.check_tool_guide_policies` (only if TOOL_GUIDE requested) → on match dispatch by action_type to `_enact_*` (BLOCK_INTENT→Command; GUIDE_PROMPT→playbook metadata with optional LLM refinement via `settings.policy.playbook_refine`; MODIFY_TOOLS / INJECT_CONTEXT / LOG_ONLY / TOOL_INJECT_DESCRIPTION / TOOL_REQUIRE_APPROVAL / FORMAT_OUTPUT→metadata) → merge guides → carry prior decisions into new metadata → append decision records → return.

**Invariant:** Fail-open at the enactment boundary is what makes fail-closed tool guarding safe to compose: an observability or matching crash must not brick every agent turn, while actual tool-call enforcement lives in ToolGuardRuntime which fails closed (see toolguard-runtime capsule). A porter who inverts these two failure modes gets either an unusable agent or silent non-enforcement.

**Probe:** `src/cuga/backend/cuga_graph/policy/tests/test_policy_observability.py:290/:319/:350` drive `check_and_enact` directly asserting decision records on returned commands/metadata; e2e playbook guidance flow pinned by `test_e2e_playbook_guidance.py`. Caveat: the exception branch itself has no direct unit test — its correctness argument is the code comment plus the surrounding deterministic tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "check_and_enact PolicyEnactment metadata command", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the single static entry returning `(Command|None, metadata|None)` with inferred targets and the blanket fail-open except; keep additive side-channel metadata for independent policies. Adapt action-type set and refinement trigger to host needs. Omit LangGraph `Command`/END coupling only if your framework lacks resumable commands — then return a sentinel instead.
