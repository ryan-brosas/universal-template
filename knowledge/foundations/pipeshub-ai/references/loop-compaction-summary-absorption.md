<!-- capsule-v2 -->
# Loop compaction with summary-marker absorption

## Source
pipeshub-ai `main@4a02110d` — `hooks/middleware/builtin/loop_compaction.py` (whole file, 218L).

## Path/Symbol
- `_COMPACTION_MARKER = "[Loop compaction:"` (:44)
- `_is_compaction_summary(msg)` (:47) — marker check on `UserMessage` with `injected=True`
- `_extract_prior_summary_lines(msg)` (:58)
- `_extract_artifact_ids(msg)` (:85), `_extract_turn_summary(msg)` (:96)
- `shape_loop_compaction(compact_every_n_turns=5, keep_recent=6, pin_first_n=1, trigger_ratio=0.6, max_summary_lines=50)` (:122)

## Signature
PRE_MODEL middleware factory; fires only when `turn_index % compact_every_n_turns == 0` AND token count > `budget * trigger_ratio` AND enough messages exist.

## Data Shape
Middle region → one injected `UserMessage`: header `[Loop compaction: N messages compressed at turn T]`, optional `[artifacts: id1, id2]` index line, then ≤50 body lines `[user] …` / `[assistant] first-line (called: names)` / `[tool:call_id] artifact:ID — summary`.

## Decisive source
```python
if _is_compaction_summary(msg):
    summaries.extend(_extract_prior_summary_lines(msg))
    continue          # absorbed, never recursively re-summarised
```

## Flow
Head = `messages[:pin_first_n]`; tail starts at `len - keep_recent` adjusted by `safe_tail_boundary`; middle is summarized deterministically (150-char user/assistant prefixes, 100-char tool previews; artifact-bearing results keep their recoverable ID instead of raw preview). Prior summaries are UNPACKED into their body lines and merged into the new summary; structural lines (header/artifacts/omission counts) are filtered and regenerated.

## Invariant
**Marker-absorbing merge prevents lossy cascade**: a summary-of-a-summary would truncate to 150 chars per pass and lose all signal; absorption keeps prior lines intact until the 50-line cap evicts oldest with a counted `[...and N earlier turns omitted]` line. The artifact index line preserves retrievability of data from 30+ turns ago.

## Probe
`tests/unit/agent_loop_lib/hooks/middleware/builtin/test_artifact_pipeline.py::TestLoopCompactionArtifactIndex::test_artifact_ids_in_summary` (:674) pins the artifact-index section in the merged summary.

## Retrieve
`codebase-memory-mcp cli search_graph --project pipeshub-ai --semantic-query '["shape_loop_compaction","compaction marker","summary merging"]'`

## Verdict
ADOPT for any long-running loop: deterministic (no LLM), turn-boundary triggered, and the marker-grammar (`_COMPACTION_MARKER` prefix + `[artifacts:` + omission counter) is part of the public contract because later passes parse it back.
