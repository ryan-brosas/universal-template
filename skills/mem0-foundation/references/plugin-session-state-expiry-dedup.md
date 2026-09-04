<!-- capsule-v2 -->
# Session-state expiry + cross-process dedup gate — how do fallback writes avoid duplicating richer agent-authored memories?

**Source:** mem0 Apache-2.0 `main@7e096155`; Codebase Memory `mem0`. **Question:** when a mechanical safety-net can write the same session a smarter writer already covered, what keeps it silent?

## Connected graph-selected seam
**Path/Symbol:** `integrations/mem0-plugin/scripts/on_pre_compact.py` consts (:46-53), stats gate in `main` (:276-287); `session_stats.py`: STATS_FILE (:21), `record_add` (:59-72).
**Signature:** `SESSION_STATE_EXPIRY_DAYS = 90`; gate: `stats.get("adds", 0) >= 1 → skip`; `record_add(category="", memory_id="") -> None`.
**Data Shape:** /tmp/mem0_session_stats_$USER.json = {adds, searches, categories[], category_counts{}, recent_ids[≤50], started}.

### Decisive source
```python
# session_state captures churn fast (active codebase, files in flight). Past
# ~3 months they're stale noise. Durable facts ... are stored separately by
# the agent without an expiration_date.
SESSION_STATE_EXPIRY_DAYS = 90
...
with open(stats_file) as f:
    stats = json.load(f)
if stats.get("adds", 0) >= 1:
    log.info("Agent stored %d memories this session — skipping fallback", stats["adds"])
    return
```

**Flow:** every successful write path calls `session_stats.record_add()` (increments adds; appends category; pushes {id,category,ts} into a 50-item ring) → later PreCompact/Stop fallback reads the SAME per-user file → any prior add suppresses the mechanical snapshot entirely.
**Invariant:** two-tier memory value: agent-authored durable facts have NO expiry; machine session_state expires in 90d; the fallback is strictly lower priority — one add anywhere wins; missing/corrupt stats file fails OPEN toward capturing (except → pass).
**Probe:** `cd $REFERENCE_ROOT/mem0 && .venv/bin/python -m pytest integrations/mem0-plugin/tests/test_session_stats.py -q`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mem0", query: "record_add session_stats", limit: 8, fields: ["name", "file"] });
```

## Verdict
Adopt the shared-counter dedup gate + tiered TTL for layered memory writers; adapt file location/locking to your concurrency level (this design is single-user-machine, no lock); omit the mem0 metadata vocabulary.
