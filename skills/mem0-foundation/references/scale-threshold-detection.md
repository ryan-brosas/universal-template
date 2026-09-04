<!-- capsule-v2 -->
# Scale-threshold detection — how do you notice "this deployment has outgrown the free path" from add results and provider counts without querying every call?

**Source:** mem0 MIT `main@8d5b7865`; Codebase Memory `mnt-hdd-utopia-inspo-memory-mem0`. **Question:** what are the exact trigger conditions (top_k size, memory-count threshold, check-interval pacing), and how does a porter read a vector-store count across backends that expose it differently?

## Connected graph-selected seam
**Path/Symbol:** `mem0/memory/notices.py`: `SCALE_MEMORY_COUNT_THRESHOLD=2000` / `CHECK_INTERVAL=100` / `TOP_K_THRESHOLD=50` (:36-38), `detect_scale_threshold_from_top_k` (:398-407), `detect_scale_threshold_from_add_result` (:410-461), `_mark_scale_memory_count_threshold_evaluated` (:1237-1259), persisted flag `memory_count_threshold_evaluated` (:442-443, :1225-1226), provider-count ladder `_get_provider_memory_count` (:1404-1448) + `_extract_count` key list (:1451-1476). Direct tests inside `tests/memory/test_notices.py` (no standalone suite file).
**Signature:** `detect_scale_threshold_from_top_k(top_k: Any) -> Optional[Tuple]`; `detect_scale_threshold_from_add_result(memory_instance, add_result) -> Optional[Tuple[str,str,None,int,int]]`.
**Data Shape:** detector returns `(trigger_source, reason, top_k|None, memory_count|None, threshold)`; add-result counting reads `result["results"]` items where `item.get("event") == "ADD"` (`_count_added_memories` :1392-1401).

### Decisive source
```python
def detect_scale_threshold_from_top_k(top_k):
    try: top_k_value = int(top_k)
    except (TypeError, ValueError): return None
    if top_k_value < SCALE_TOP_K_THRESHOLD: return None      # 50
    return ("top_k", "high_top_k", top_k_value, None, SCALE_TOP_K_THRESHOLD)

# paced check: first call always evaluates; afterwards only every +100 added memories
with _state_lock:
    if _scale_memory_count_threshold_evaluated_in_process: return None
    _scale_memory_count_adds_since_check += added_count
    should_check = (not _scale_memory_count_checked_in_process
                    or _scale_memory_count_adds_since_check >= SCALE_MEMORY_COUNT_CHECK_INTERVAL)
    if not should_check: return None
    _scale_memory_count_checked_in_process = True
    _scale_memory_count_adds_since_check = 0
    ...
if provider_count is None or provider_count < 2000: return None

def _extract_count(info):   # five spellings of "how many vectors", dict → pydantic → attrs
    for key in ("count","points_count","vectors_count","indexed_vectors_count","num_docs"):
        ...
```

**Flow:** search calls probe top_k ≥50 instantly (stateless); add calls accumulate ADD-event counts and gate the expensive provider count query to once at start then every 100 adds → threshold evaluation is ONCE-EVER: both an in-process latch and a persisted `memory_count_threshold_evaluated` flag (written by `_mark_...` BEFORE returning the trigger, and again inside `_record_scale_threshold_opportunity`) prevent re-firing after restarts → count resolution tries `vector_store.count()` callable, then `col_info(name)` with TypeError-tolerant zero-arg fallback, then `client.count(index=name)`; values accepted as dict keys, pydantic `.model_dump()`, or plain attributes.
**Invariant:** (1) top_k detector is intentionally UNLOCKED by telemetry state — pure arithmetic on the argument; (2) memory-count evaluation happens at most ONCE per deployment lifetime (persisted boolean), not per window; (3) the interval counter resets only when a check actually runs, so bursts between checks accumulate rather than drop; (4) count extraction must tolerate qdrant-style `points_count`, faiss `count`, and object-vs-dict shapes or one backend silently never triggers; (5) all failures (bad ints, missing vector_store, exceptions in count) degrade to None — never raise into add/search.
**Probe:** `tests/memory/test_notices.py` scale-threshold cases (top_k boundary via int-coercion negatives; interval pacing asserted against reset globals in the autouse fixture).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-mem0", query: "_get_provider_memory_count detect_scale_threshold_from_add_result _extract_count", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the once-ever threshold latch + interval pacing and the multi-key count ladder verbatim; adapt thresholds (50/100/2000) to your product's scale story; omit the col_info/client fallbacks if you control the single backend (keep the coerce-nonneg-int guard either way).
