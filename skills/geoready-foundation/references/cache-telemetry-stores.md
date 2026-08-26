<!-- capsule-v2 -->
# FileCache & telemetry stores — TTL'd response cache with size eviction, closed-vocabulary event store

**Source:** GeoReady (Geo Optimizer) MIT `main@a7165be2`; Codebase Memory `ext-aeo-geo-optimizer-skill`. **Question:** How do the supporting stores keep dev re-runs cheap and usage analytics honest?

## SHA-256-keyed JSON cache + frozen event-type set
**Path/Symbol:** `src/geo_optimizer/utils/cache.py:FileCache` (26–126); `src/geo_optimizer/core/telemetry.py:TelemetryStore.record` (76–110).
**Signature:** `FileCache(cache_dir=~/.geo-cache, ttl=3600).get(url) -> (status, text, headers) | None`; `.put(url, status_code, text, headers)`; `TelemetryStore.record(event_type, *, domain="", data=None)`.
**Data Shape:** one JSON file per URL (`sha256(url).json`) holding `{url, status_code, text, headers, cached_at}`; cache cap 500 MB with oldest-mtime eviction; telemetry table `geo_events(event_type, recorded_at, domain, data JSON)` indexed `(type, recorded_at DESC)` and `(domain, recorded_at DESC)`.

### Decisive source
```python
# get(): corrupt cache = miss, never an exception
try:
    data = json.loads(path.read_text(encoding="utf-8"))
except (json.JSONDecodeError, OSError):
    return None
if time.time() - cached_at > self.ttl:
    path.unlink(missing_ok=True)
    return None

# telemetry: unknown event names raise — typos cannot silently vanish
if event_type not in _GEO_EVENT_TYPES:   # frozenset of 5 geo_* events
    raise ValueError(f"Unknown event type: {event_type}. Expected one of: {sorted(_GEO_EVENT_TYPES)}")
```

**Flow:** audit passes `use_cache=True` → `get` returns a `CachedResponse(status_code, text, content, headers)` dataclass shaped like a requests.Response so all downstream audits run unmodified (fix #83); `put` evicts beyond 500 MB then writes atomically; opt-in only (`--cache`). Telemetry wraps five semantic events (`geo_audit_run`, `geo_score_improved`, `geo_suggestion_applied`, `geo_api_error`, `geo_badge_generated`) with `get_latest_audit_score(url)` powering delta events without touching HistoryStore.
**Invariant:** Cache reads must tolerate corruption/absence silently (dev tool must not crash on its own cache); TTL expiry deletes rather than ignores, keeping the dir bounded. Event vocabulary is CLOSED at module scope — analytics consumers can rely on exact strings.
**Probe:** `tests/test_telemetry.py::test_record_rejects_unknown_event` (+ `tests/test_core.py` cache tests; `PYTHONPATH=src pytest tests/test_telemetry.py -q` green at pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-geo-optimizer-skill", query: "FileCache telemetry record", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt tolerant-read TTL cache + closed event vocabularies for local-first tooling; adapt limits/event sets; omit eviction policy if your storage differs.
