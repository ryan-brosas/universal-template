<!-- capsule-v2 -->
# Blocked-output retention rules — which items of a rejected final turn survive into the session?

**Source:** OpenAI Agents Python MIT `main@cb8a2e7e`; Codebase Memory project `openai-agents-python`. **Question:** When an output guardrail rejects the final answer, which of that turn's items must still be persisted so the next request replays correctly?

## Side-effect retention + reasoning-tying
**Path/Symbol:** `src/agents/run_internal/run_loop.py:` `_SIDE_EFFECT_ITEM_TYPES` (:461), `_reasoning_indexes_tied_to_retained_items` (:464–492), `_retained_items_for_blocked_output` (:495–516).
**Signature:** `def _retained_items_for_blocked_output(items: list[RunItem]) -> list[RunItem]`.
**Data Shape:** `_SIDE_EFFECT_ITEM_TYPES = frozenset({"tool_call_item", "tool_call_output_item"})`; retention computed as index sets, then materialized in original order.

### Decisive source
```python
_SIDE_EFFECT_ITEM_TYPES = frozenset({"tool_call_item", "tool_call_output_item"})
# ``_SIDE_EFFECT_ITEM_TYPES`` is enumerated rather than derived, so an item type added later is
# *discarded* here by default and has to be classified deliberately. A record of a side effect
# that goes unclassified is a bug, so the safer default is the one that surfaces as a missing item
# rather than as a rejected message quietly reaching the session.
...
retained_indexes |= _reasoning_indexes_tied_to_retained_items(items, retained_indexes)
return [item for index, item in enumerate(items) if index in retained_indexes]
```
Reasoning association rule (same as `items._drop_reasoning_items_preceding_dropped_calls`): a reasoning item belongs to the NEXT non-reasoning model-emitted item; keeping a group whose follower was dropped would leave a dangling reasoning item (API rejects: "reasoning was provided without its required following item"); dropping a group whose follower is retained strips needed replay context. A TRAILING reasoning group (no following item at all) is dropped — stricter than upstream reference because the turn is complete.

**Flow:** enumerate indexes whose type ∈ side-effect set → union with tied reasoning indexes → emit retained items in model order. Everything else — above all the assistant message the guardrail rejected — is discarded.

**Invariant:** Default-deny classification: new item types are DROPPED until deliberately added (a silently-persisted rejected message is worse than a temporarily missing item). Reasoning-to-follower coupling must be preserved bidirectionally with the drop-side rule in the items module or requests 400.

**Probe:** `tests/test_run_state.py` and `tests/test_handoff_history_duplication.py` exercise reasoning-attachment rules around retained/dropped items (same association grammar).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "retained items blocked output reasoning tied", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the default-deny retention set + reasoning-tying invariant verbatim for any provider whose API couples hidden-reasoning items to following outputs; adapt the type strings to your item taxonomy; omit the trailing-group strictness note only if your histories can receive later items for the same turn.
