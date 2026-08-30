<!-- capsule-v2 -->
# Expiration filter — how do memories expire by date without a reaper job touching the store?

**Source:** mem0 MIT `main@001c2352`; Codebase Memory `mem0`. **Question:** how is per-memory TTL implemented as read-time filtering, and where must the expiry check run?

## Connected graph-selected seam
**Path/Symbol:** `mem0/memory/main.py`: `_normalize_expiration_date` (:427-439), `_payload_is_expired` (:442-451); filtered in `_get_all_from_vector_store` (:1355), `_search_vector_store` candidate loop (:1670); stored via `add` (:820, :828-829); cleared/changed via `update` (:1857-1859).
**Signature:** `_payload_is_expired(payload) -> bool`; `expiration_date: Any` accepted as `datetime | date | str(YYYY-MM-DD)`.
**Data Shape:** payload key `expiration_date` = ISO date string (date only, no time); comparison against `datetime.now(timezone.utc).date()`.

### Decisive source
```python
try:
    return date.fromisoformat(str(expiration_date)) < datetime.now(timezone.utc).date()
except ValueError:
    return False    # unparsable date => NOT expired
```

**Flow:** on add, normalize any accepted input shape to an ISO date string into metadata; on every READ path (search candidates and get_all rows; `show_expired=True` bypasses both), skip payloads whose expiration_date is strictly before today UTC; update can set a new date or pass `None` to clear it. Nothing is ever deleted at expiry — the row stays until normal deletion.
**Invariant:** expiry is a READ-TIME predicate, never a background sweep — a porter who deletes expired rows on write breaks undo/history; unparsable dates fail OPEN (visible) not closed; strict `<` means a memory expires the day AFTER its date (the date itself is still live); the check runs BEFORE formatting so expired rows don't consume output budget — get_all over-fetches `max(limit*4, 60)` precisely to refill after expiry skips.
**Probe:** `tests/test_main.py::test_add_stores_expiration_date` (:69), `test_get_all_hides_expired_memories_by_default`, `test_get_all_can_show_expired_memories`; `tests/memory/test_main.py::test_async_update_can_change_expiration_date_without_changing_text` (:216).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mem0", query: "_payload_is_expired expiration_date show_expired", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt read-time expiry with fail-open parsing and the over-fetch-to-refill pattern; adapt the accepted input shapes; omit platform-side temporal indexes.
