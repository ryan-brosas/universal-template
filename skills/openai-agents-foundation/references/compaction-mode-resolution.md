<!-- capsule-v2 -->
# Compaction mode resolution — when may history be replaced by reference (previous_response_id) and when must it be resent (input)?

**Source:** OpenAI Agents Python MIT `main@fe45b415`; Codebase Memory project `openai-agents-python`. **Question:** A compaction request can point at the stored server response or resend the whole transcript — what decides, and why is an unstored-response memory needed?

## The mode ladder
**Path/Symbol:** `src/agents/memory/openai_responses_compaction_session.py`: `_resolve_compaction_mode` (:592–604), the `auto`+unstored override `_resolve_compaction_mode_for_response` (:153–168), `_last_unstored_response_id` bookkeeping in `run_compaction` (:184–191), threshold default (`DEFAULT_COMPACTION_THRESHOLD = 10`, :28) and candidate selection `select_compaction_candidate_items` (:34–55).
**Signature:** `def _resolve_compaction_mode(requested_mode: Literal["previous_response_id","input","auto"], *, response_id: str | None, store: bool | None) -> Literal["previous_response_id","input"]`.
**Data Shape:** decision context dict passed to hooks: `{response_id, compaction_mode, compaction_candidate_items, session_items}`; candidates exclude user messages and prior `compaction` items.

### Decisive source
```python
def _resolve_compaction_mode(requested_mode, *, response_id, store):
    if requested_mode != "auto": return requested_mode
    if store is False:        return "input"   # nothing stored server-side to reference
    if not response_id:       return "input"
    return "previous_response_id"
# auto + explicit store=False this turn ⇒ remember and force input NEXT time too:
if store is False and self._response_id: self._last_unstored_response_id = self._response_id (:186-187)
```
and in `_resolve_compaction_mode_for_response`: `auto ∧ store is None ∧ response_id == self._last_unstored_response_id ⇒ "input"` (:161–167).

**Flow:** non-auto modes are honored verbatim → auto consults THIS turn's `store` flag → falls back to input when there's no response id → otherwise references the server copy. Because a `store=False` run leaves NO retrievable response, the session remembers that id so a later hook-driven compaction that sees only `store=None` still refuses `previous_response_id`. `previous_response_id` without any id raises ValueError (:198–202).
**Invariant:** Referential compaction is only legal while the referenced response actually exists server-side. Missing the unstored-memory case silently corrupts history replacement (compact against a nonexistent id / empty base).
**Probe:** `grep -n "store is False" src/agents/memory/openai_responses_compaction_session.py` → 2 hits (:186 unstored-memory write, :600 mode ladder). Direct tests: `tests/memory/test_openai_responses_compaction_session.py::test_run_compaction_auto_uses_input_when_store_false` (:382), `..._auto_uses_input_when_last_response_unstored` (:450), `..._run_compaction_requires_response_id` (:169), `TestSelectCompactionCandidateItems::test_excludes_user_messages` (:68).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "_resolve_compaction_mode previous_response_id auto unstored", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-way mode ladder plus the unstored-response memory; adapt thresholds/hook vocabulary; omit OpenAI-specific compact API shapes. Direct tests cover all four branches.
