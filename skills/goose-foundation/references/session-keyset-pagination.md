<!-- capsule-v2 -->
# Session list keyset pagination — how do you page sessions by "last activity" without OFFSET instability?

**Source:** goose Apache-2.0 `main@2eb3ab1001dedb5ab09a6ed60158adfc248bac56`; Codebase Memory `goose`. **Question:** How do I page a session list sorted by derived last-activity time (messages may be newer than the row's updated_at), with stable cursors, filters, and optional previews?

## Keyset pagination plane
**Path/Symbol:** `crates/goose/src/session/session_manager.rs` : `SessionStorage.list_sessions_matching` (1933-2035), `list_sessions_paged` (2048-2090); `SessionListCursor/Page/Filters/PageQuery` (319-345).
**Signature:** `async fn list_sessions_paged(&self, query: SessionListPageQuery<'_>) -> Result<SessionListPage>`.
**Data Shape:** `SessionListCursor { sort_at: DateTime<Utc>, session_id: String }`; page = `{sessions: Vec<Session>, next_cursor: Option<_>}`; filters = types / working_dir / keyword / only_sessions_with_messages.

### Decisive source
```sql
COALESCE(MAX(CASE WHEN m.created_timestamp > 10000000000 THEN m.created_timestamp/1000
                  ELSE m.created_timestamp END), unixepoch(s.updated_at)) as sort_timestamp
...
HAVING (sort_timestamp < ? OR (sort_timestamp = ? AND s.id < ?))
ORDER BY sort_timestamp DESC, s.id DESC
LIMIT ?
```
```rust
let mut sessions = self.list_sessions_matching(/* limit: Some(page_size + 1) */).await?;
let has_next_page = sessions.len() > page_size;
let next_cursor = has_next_page.then(|| {
    let anchor = &sessions[page_size - 1];          // anchor = last RETURNED row,
    SessionListCursor { sort_at: session_sort_at(anchor), session_id: anchor.id.clone() }
});
if has_next_page { sessions.truncate(page_size); }
if include_last_message_snippet {
    super::last_message_snippet::hydrate_last_message_snippets(pool, &mut sessions).await?;
}
```
Keyword filter joins `EXISTS (... json_each(content_json) WHERE type='text' AND instr(LOWER(text), ?) > 0 OR-joined per term)` restricted to `userVisible` rows; empty types-slice short-circuits to empty page; LIKE wildcards in terms are literal (instr-based).

**Flow:** build WHERE from filters → cursor becomes HAVING tuple comparison `(sort,id) < (cursor)` → fetch page_size+1 → detect continuation → anchor cursor at the last row that will be RETURNED → truncate → hydrate snippets only for returned rows.
**Invariant:** Sorting is by DERIVED activity (`COALESCE(max message ts, updated_at)`), never `updated_at` alone; cursor is a keyset tuple so concurrent inserts cannot duplicate or skip rows; the lookahead row is never returned; pagination happens BEFORE snippet hydration.
**Probe:** tests `test_session_list_paged_first_second_and_final_page`, `..._sorts_by_last_message_at` (older-updated but newer-message session ranks first), `..._uses_id_tiebreaker_for_duplicate_activity_time`, `..._filters_empty_and_cwd_before_pagination`, `..._keyword_treats_like_wildcards_as_literals`. Run: `cargo test -p goose --lib session::session_manager`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "goose", query: "list_sessions_paged keyset cursor sort_timestamp lookahead snippet hydration", limit: 8, fields: ["lines"] });
```

## Verdict
Adopt: derived sort key, HAVING-tuple keyset cursor, page_size+1 lookahead anchored on the last returned row, post-pagination preview hydration. Adapt filter vocabulary to your host. Omit goose's SessionType taxonomy and ACP consumers.
