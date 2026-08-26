<!-- capsule-v2 -->
# Last-message snippet hydration — how do you attach a bounded preview to every session in a list page with ONE query?

**Source:** goose Apache-2.0 `main@2eb3ab1001dedb5ab09a6ed60158adfc248bac56`; Codebase Memory `goose`. **Question:** How do I show "last message" previews for a page of sessions without N+1 queries or unbounded scans, when the latest rows may be tool calls or hidden context?

## Bounded hydration plane
**Path/Symbol:** `crates/goose/src/session/last_message_snippet.rs` : `hydrate_last_message_snippets` (22-57), `recent_message_rows` (59-96), `message_from_recent_row` (98-120), `message_snippet` (129-154).
**Signature:** `pub(super) async fn hydrate_last_message_snippets(pool: &Pool<Sqlite>, sessions: &mut [Session]) -> Result<()>`.
**Data Shape:** Constants `LAST_MESSAGE_SNIPPET_MAX_CHARS = 128`, `RECENT_MESSAGE_SNIPPET_SCAN_LIMIT = 8`; fills `session.last_message_snippet: Option<String>` (None ⇒ render nothing).

### Decisive source
```rust
// one UNION ALL of per-session bounded subqueries — no N+1:
let branch = r#"SELECT ... FROM (
    SELECT id AS row_id, ..., metadata_json, message_id FROM messages
    WHERE session_id = ? ORDER BY created_timestamp DESC, id DESC LIMIT ?)"#;
let sql = std::iter::repeat_n(branch, session_ids.len()).collect::<Vec<_>>().join(" UNION ALL ");
// first parseable user-visible TEXT row per session wins:
for row in rows {
    if snippets.contains_key(&row.session_id) { continue; }
    ...
}
```
```rust
fn message_snippet(message: &Message, max_chars: usize) -> Option<String> {
    if !message.metadata.user_visible { return None; }
    let text = message.content.iter()
        .filter_map(|c| c.filter_for_audience(Role::User))
        .filter_map(|c| c.as_text().map(|t| t.to_string()))
        .collect::<Vec<_>>().join("\n");
    let normalized = text.split_whitespace().collect::<Vec<_>>().join(" ");
    // char-boundary truncation + ellipsis ONLY when truncated:
    let mut result: String = chars.by_ref().take(max_chars).collect();
    if chars.next().is_some() { result.truncate(result.trim_end().len()); result.push('…'); }
    Some(result)
}
```

**Flow:** collect page session ids → single UNION ALL query (≤8 newest rows per session) → global re-sort (session asc, ts desc, row_id desc) → walk rows, skipping sessions already resolved and rows that are non-text/tool/thinking/unparseable → map lookup fills each session's field (missing ⇒ None).
**Invariant:** Work is O(page × 8) regardless of history length; unparseable JSON never aborts hydration (falls back to older rows); snippets are pure user-visible text (assistant-audience blocks excluded) collapsed to single spaces; the '…' appears exactly when content was cut.
**Probe:** tests `test_live_last_message_snippets_read_from_recent_messages`, `..._skips_unparseable_recent_rows` (invalid-JSON newer row falls back to older text), `..._stays_bounded` (8 hidden messages ⇒ None), `..._ignores_tool_messages`, `..._reads_truncated_conversation`. Run: `cargo test -p goose --lib session::last_message_snippet`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "goose", query: "hydrate_last_message_snippets message_snippet user visible truncate ellipsis", limit: 8, fields: ["lines"] });
```

## Verdict
Adopt: UNION ALL batched preview fetch, first-parseable-wins resolution, user-audience text-only projection with char-safe truncation. Adapt limits and visibility keys. Omit goose Session coupling.
