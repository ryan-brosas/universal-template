<!-- capsule-v2 -->
# Timeline → trajectory JSONL export — how do you turn recorded runs into eval/RL dataset rows without entangling the store?

**Source:** pipeshub-ai (Apache-2.0) `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** A porter building an offline eval harness (or RL episode dump) must know how one run becomes ONE JSONL line — the grouping key, the sort contract, and the multi-agent trace split.

## entries_to_trajectory / entries_to_trajectories
**Path/Symbol:** `eval/trajectory.py:entries_to_trajectory` (37-56), `entries_to_trajectories` (59-69), `timeline_entry_to_step` (25-34), async fetchers `export_run_trajectory`/`export_trace_trajectories`/`export_trace_to_jsonl` (72-106), `write_jsonl`/`read_jsonl` (85-98).
**Signature:** `entries_to_trajectory(entries: list[TimelineEntry]) -> dict`; `entries_to_trajectories(entries: list[TimelineEntry]) -> list[dict]`; `write_jsonl(trajectories, path)` / `read_jsonl(path) -> list[dict]`.
**Data Shape:** One trajectory dict = header fields from the FIRST ordered entry (`run_id`, `trace_id`, `agent_id`, `parent_run_id`, `role_name`, `model`) + `final_status` from the LAST ordered entry + `steps: list[dict]` (`sequence_id`, `timestamp`, status `.value`, `event_type`, `summary`, `detail`). Empty input raises `ValueError` — never silently emits a hollow record.

### Decisive source
```python
# trajectory.py — the run is the unit; sequence order is reconstructed, not assumed
if not entries:
    raise ValueError("entries_to_trajectory() requires at least one TimelineEntry")
ordered = sorted(entries, key=lambda e: e.sequence_id)
first = ordered[0]
return {..., "final_status": ordered[-1].status.value ...,
        "steps": [timeline_entry_to_step(e) for e in ordered]}

def entries_to_trajectories(entries):            # whole trace → one row PER run_id
    by_run: dict[str, list[TimelineEntry]] = {}
    for entry in entries:
        by_run.setdefault(entry.run_id, []).append(entry)
    trajectories.sort(key=lambda t: t["steps"][0]["sequence_id"])
```

**Flow:** group flat entries by run_id → per run: sort by sequence_id → flatten steps → attach parent_run_id so downstream tools can rebuild the spawn tree → order rows by each run's first step → JSONL write (one object per line, parents mkdir).
**Invariant:** The GROUPING KEY is run_id, never trace_id — a trace spans parent + spawned children and MUST export as one row per run with parent_run_id preserved (the docstring's stated contract). Sorting is always by sequence_id regardless of store return order. Module is deliberately standalone (no CLI wiring; only depends on the abstract TimelineStore) so it can be pointed at any backend.
**Probe:** no direct unit test exists under `tests/` for `eval/trajectory.py` (coverage caveat — source-grounded probe only). Deterministic check: `SkillLearning._learn` (hooks/middleware/builtin/skill_learning.py:110-117) consumes exactly these functions per-run before extraction, confirming the run-scoped call pattern.
**Coverage caveat:** graph coverage `no_recorded_issue`+`metadata_match`, but no direct test pins behavior — qualify claims when reusing.
