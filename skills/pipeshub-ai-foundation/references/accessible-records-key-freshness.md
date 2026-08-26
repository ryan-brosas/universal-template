<!-- capsule-v2 -->
|# Accessible-records key taxonomy + hash-field freshness — how do you cache per-user permission maps in Redis without SCAN and without immortal fields?

## Three key classes (kb / capp / cusr); record-level ACLs live one-hash-per-connector with field=user, and each hash field carries its OWN timestamp because Redis expires whole keys only
**Path/Symbol:** `backend/python/app/services/cache/accessible_records_cache.py` :70–163 (`KEY_PREFIX="pipeshub:accessible_records:v1"` :73, env knobs :74–78, `_kb_key/_app_connector_key/_user_connector_key` :155–162) and freshness envelope `_read` :221–252 / `_write` :254–263.
**Signature:** `_get_or_compute(key: str, field: str | None, loader)`; string ops when `field is None`, hash ops otherwise.
**Data Shape:** string values = plain JSON map `{"virtualRecordId": "recordId"}` with key-level TTL (`set(..., ex=ttl)`). Hash values = envelope `{"t": int(time.time()), "m": {map}}` per user field; key TTL REFRESHED by every user's write (`hset` then `expire`). Corrupt/non-dict JSON ⇒ treated as a miss; envelope missing numeric `t` or dict `m` ⇒ miss; `time.time() - t > ttl` ⇒ miss.

### Decisive source
```python
# Hash fields carry their own timestamp: Redis expires whole keys only,
# and the key's TTL is refreshed by every other user's write, so a field
# would otherwise live forever under steady traffic.
if not isinstance(written_at, (int, float)) or not isinstance(stored, dict):
    return None
if time.time() - written_at > self._ttl:
    return None
return stored
```

**Flow:** module docstring states the design: KB/app-level connectors produce USER-INDEPENDENT maps (shared by every org member; only which KBs/apps a user may reach is resolved live), record-level connectors sync real per-record ACLs ⇒ keyed PER USER inside ONE hash per connector so "a single DEL invalidates every user at once, with no SCAN and no set-index". Every entry carries a TTL because event-driven invalidation is best-effort by design.
**Invariant:** the granularity you compute at is the granularity you cache at — merging everything into one blob would force full invalidation on any single connector sync. Empty maps ARE cached (a user with no access must not re-run the traversal per search).
**Probe:** `backend/python/tests/unit/services/cache/test_accessible_records_cache.py::TestKeySchema::test_keys_are_namespaced_and_org_scoped` (:101), `::test_user_connector_entries_are_per_user` (:158 asserts `{user-a, user-b}` fields in one hash), `TestHashFreshness::test_stale_field_is_recomputed` (:178), `::test_envelope_without_timestamp_is_a_miss` (:202).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "AccessibleRecordsCache get_or_compute_user_connector kb_key", limit: 10 });
```

## Verdict
Adopt the three-class key schema, per-user hash fields with self-timestamped envelopes under a refreshed key TTL, and empty-map caching; adapt the key prefix/env names; omit Arango-specific traversal behind your own loader. Direct tests ship upstream (492-line suite covering this exact class).
