<!-- capsule-v2 -->
# parent_results budget ladder (digest preview + _meta'd JSON file, never silent drops)

## Source
pipeshub-ai Apache-2.0 `main@4a02110d`; Codebase Memory `pipeshub-ai`. **Question:** How do you hand a child both a skim-readable digest AND full-fidelity data without one huge tool result blowing its context?

## Path/Symbol
`tools/builtin/coordination/parent_results.py` — `format_parent_results_digest(results, per_result_chars=8_000, total_chars=48_000)` (:171–201), `parent_results_as_json(results, max_bytes=2MiB)` (:238–339), `_truncate_content` (:216–235). Consumed by `agent_tool.py::handle` with `PARENT_RESULTS_INPUT_PATH` staging (:253–270).

## Signature
Digest: per-result truncate → running-total spend; once budget spent, remaining results COUNTED (`"... [N more result(s) omitted for length — see the full data file noted below]"`), never silently dropped. JSON: `{"_meta": {truncated, total_results, included_full, included_truncated, skipped}, "results": [{tool, content}]}`.

## Data Shape
JSON path: try `json.loads` per result first (most tool results are already JSON-encoded strings — child gets structured data, not double-encoded JSON :204–213); over-budget ⇒ reserve 512B overhead, equal per-result budget in CHRONOLOGICAL order (primary gathering calls come first), then: fits→full / ≥100B left→truncate content at `remaining-80` / else skip; after the FIRST truncation all later entries are metadata-only (single break :314); skipped tools echoed in `payload["_skipped"]`.

### Decisive source
```python
Returns ``None`` only when ``results`` is empty.  For non-empty input
the file is ALWAYS produced — oversized payloads are truncated
per-result rather than silently dropped.
```

**Flow:** collect → dependency results merged ahead of tool results (test :220–240) → digest prepended to goal with an anti-fabrication header ("do NOT ask for it, claim it is unavailable, or fabricate placeholder data") + pointer to the staged full file → JSON payload staged into child sandbox via stage_input_files. Two channels cover both a model that reads its goal and one that doesn't.

**Invariant:** The digest is explicitly a CONVENIENCE PREVIEW — full fidelity lives in the file. Every degradation is VISIBLE (truncation markers, _meta counters, _skipped list): the child can always tell whether it saw everything. Chronological-first ordering is deliberate (earliest = primary data).

**Probe:** `tests/unit/agent_loop_lib/tools/builtin/coordination/test_parent_results.py` — digest caps :121–143 (`"more result(s) omitted"` pinned), json round-trip :146–170 (`_meta.truncated`, structured decode), dependency extraction+merge-order :173–240.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph --project pipeshub-ai --semantic-query '["format_parent_results_digest","parent_results_as_json","PARENT_RESULTS_INPUT_PATH"]'
```

## Verdict
Adopt dual-channel handoff (goal digest + sandbox file) and count-don't-hide degradation; adapt caps/path constants.
