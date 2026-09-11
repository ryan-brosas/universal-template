<!-- capsule-v2 -->
# Session message ordering invariants — how does a seconds-resolution timestamp column still replay conversations in arrival order?

**Source:** goose Apache-2.0 `main@2eb3ab1001dedb5ab09a6ed60158adfc248bac56`; Codebase Memory `goose`. **Question:** When stored timestamps have 1-second resolution and messages can be constructed before they are appended, how do I guarantee read-back order and safe truncation boundaries?

## Ordering kernel
**Path/Symbol:** `crates/goose/src/session/session_manager.rs` : `SessionStorage.get_conversation` (1801-1837), `SessionStorage.add_message` (1839-1882), `truncate_conversation_from_message` (2440-2470).
**Signature:** `async fn get_conversation(&self, session_id: &str) -> Result<Conversation>` / `async fn add_message(&self, session_id: &str, message: &Message) -> Result<()>`.
**Data Shape:** `messages(id INTEGER PK AUTOINCREMENT, message_id TEXT, session_id, role, content_json, created_timestamp INTEGER seconds, metadata_json)`; index `idx_messages_session_created(session_id, created_timestamp, id)`.

### Decisive source
```rust
// Order by created_timestamp, then by id to break ties. created_timestamp is in seconds,
// so messages created in the same second (e.g., tool request and response) need to
// maintain their insertion order via the auto-increment id.
"... FROM messages WHERE session_id = ? ORDER BY created_timestamp, id"
```
```rust
// Messages are read back ordered by (created_timestamp, id), so one built
// before the messages it is appended after would sort ahead of them —
// operations do that whenever they prepare a reply and fill it in while a
// tool runs. Never move a message ahead of what is already stored.
let latest: Option<i64> = sqlx::query_scalar(
    "SELECT MAX(created_timestamp) FROM messages WHERE session_id = ?")...;
let created = message.created.max(latest.unwrap_or(message.created));
```
Truncation deletes `(created_timestamp > ? OR (created_timestamp = ? AND id >= ?))` after resolving the boundary row `ORDER BY created_timestamp, id LIMIT 1` — same-second EARLIER rows survive.

**Flow:** append → clamp timestamp to at-least the current MAX(stored) → insert → bump `sessions.updated_at`. Read → ORDER BY `(created_timestamp, id)`. Truncate-by-message-id → find boundary (ts,id) → delete that row and everything strictly after in tuple order.
**Invariant:** Arrival order is authoritative: a late-stamped message never overtakes already-stored rows; truncation removes exactly the boundary row plus later rows even when several rows share one second. `replace_conversation` rewrites rows verbatim (no clamp) — callers own ordering there.
**Probe:** tests `messages_read_back_in_the_order_they_arrived`, `test_truncate_conversation_from_message_keeps_same_second_previous_rows`, `test_messages_session_created_index_avoids_disk_sort`, `test_last_message_at_is_derived_from_messages`. Run: `cargo test -p goose --lib session::session_manager`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "goose", query: "add_message created_timestamp monotonic ordering get_conversation tiebreak truncate boundary", limit: 8, fields: ["lines"] });
```

## Verdict
Adopt: composite (timestamp, autoincrement-id) ordering, monotonic write clamp for pre-constructed messages, tuple-boundary truncation, and the covering index that makes the sort disk-free. Adapt the clamp policy if your host stamps at insert time only. Omit goose's Message/Conversation reconstruction details.
