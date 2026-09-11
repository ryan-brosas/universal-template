<!-- capsule-v2 -->
# Policy Decision Observability — an append-only, checkpoint-safe audit trail riding on graph metadata

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How do you expose every policy decision (matched/blocked/approved/denied, per stage) to UIs and audits when LangGraph state updates replace metadata wholesale?

## policy_decisions ledger with dedupe + carry-forward
**Path/Symbol:** `src/cuga/backend/cuga_graph/policy/observability.py` (`POLICY_DECISIONS_KEY` :15, `_ACTION_BY_METADATA_TYPE` :17-26, `decision_from_match` :29-59, `decision_from_metadata` :62-109, `append_policy_decisions` :112-128, `carry_policy_decisions` :139-144, `_valid_policy_decisions` :160-168); model `PolicyDecision` in `models.py:405-420`.

**Signature:** `append_policy_decisions(metadata: dict, decisions: Iterable[Optional[PolicyDecision]]) -> list[PolicyDecision]`; `carry_policy_decisions(source: Optional[dict], target: dict) -> list[PolicyDecision]`.

**Data Shape:** `PolicyDecision{policy_id, policy_name, policy_type, action_type?, stage: input|tool|output, outcome: matched|applied|blocked|approval_required|approved|denied, confidence?, reasoning?, tool_name?, agent_name?}` stored as JSON-safe dicts under `metadata["policy_decisions"]`.

### Decisive source
```python
# observability.py:112-127 — append with identity dedupe, always re-serialized
existing = _valid_policy_decisions(metadata.get(POLICY_DECISIONS_KEY) or [])
identities = {_decision_identity(item) for item in existing}
for decision in decisions:
    if decision is None:
        continue
    identity = _decision_identity(decision)
    if identity not in identities:
        existing.append(decision)
        identities.add(identity)
metadata[POLICY_DECISIONS_KEY] = [item.model_dump(mode="json") for item in existing]
# observability.py:160-168 — why lenient parsing is safe:
# "Ignore stale malformed entries so observability cannot disable enforcement."
```
Identity tuple (:147-157): `(policy_id, policy_type, stage, outcome, tool_name, agent_name)`. Carry-forward (`enactment.py:183`) merges the previous metadata's trail into each new decision payload before it's written onto a Command, so blocking commands remain "the single checkpointed source of truth".

**Flow:** any enactment point builds a decision from a live match or from already-stored metadata (mapping legacy `policy_type` strings like `tool_restriction`/`context_injection`/`log_only` onto action types via `_ACTION_BY_METADATA_TYPE`; first matched/required tool becomes `tool_name`) → appended into whichever metadata survives → approval handler appends APPROVED/DENIED at resume time → server layer serializes the list for UI badges.

**Invariant:** The ledger is strictly additive and idempotent per identity; it must never throw on bad entries (drop them instead), because an observability failure that propagated would either kill runs or — worse — tempt future maintainers into disabling enforcement to fix logging.

**Probe:** `src/cuga/backend/cuga_graph/policy/tests/test_policy_observability.py` (drives `check_and_enact`, asserts decisions recorded for blocked intents and guide applications; malformed-entry tolerance covered by the validators' try/except paths). Caveat: `test_utils.py` is small (2KB) — most coverage here flows through the e2e suites' metadata assertions.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "append_policy_decisions carry_policy_decisions PolicyDecision", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the metadata-riding decision ledger with identity dedupe, stage/outcome enums, and lenient deserialization. Adapt where the trail lives if your framework has first-class run events. Omit agent_name delegation fields unless you have multi-agent routing.
