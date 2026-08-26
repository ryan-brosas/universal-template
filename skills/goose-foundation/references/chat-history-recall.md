<!-- capsule-v2 -->
# Chat-history recall gates — how do you search persisted conversations without leaking hidden or operational content?

**Source:** goose Apache-2.0 `main@2eb3ab1001dedb5ab09a6ed60158adfc248bac56`; Codebase Memory `goose`. **Question:** How do I implement cross-session chat recall that respects audience visibility, excludes turn-context noise, and returns session-grouped results?

## Recall filter plane
**Path/Symbol:** `crates/goose/src/session/chat_history_search.rs` : `ChatHistorySearch` (50-58), `execute` (81-96), `build_sql` (133-213), `process_rows` (215-250), `extract_text_content` (252-265), `get_session_totals` (267-299), `convert_to_results` (301-347).
**Signature:** `ChatHistorySearch::new(pool, query, limit: Option<usize> /* default 10 */, after_date, before_date, exclude_session_id, session_types) -> Self` + `pub async fn execute(self) -> Result<ChatRecallResults>`.
**Data Shape:** `ChatRecallResults { results: Vec<ChatRecallResult>, total_matches }`; result groups messages per session with `last_activity` and `total_messages_in_session`.

### Decisive source
```sql
WHERE COALESCE(CASE WHEN json_valid(m.metadata_json)
        THEN json_extract(m.metadata_json,'$.agentVisible') END, 1) = 1   -- default-allow
AND COALESCE(CASE WHEN json_valid(m.metadata_json)
        THEN json_extract(m.metadata_json,'$.turnContext') END, 0) = 0    -- exclude ops context
AND EXISTS (SELECT 1 FROM json_each(m.content_json) AS content
    WHERE json_extract(content.value,'$.type') = 'text'
    AND (json_type(content.value,'$.annotations.audience') IS NULL
         OR EXISTS (SELECT 1 FROM json_each(content.value,'$.annotations.audience') AS audience
                    WHERE audience.value = 'assistant'))
    AND ( LOWER(json_extract(content.value,'$.text')) LIKE ? OR ... ))
```
```rust
fn parse_keywords(&self) -> Vec<String> {
    self.query.split_whitespace().map(|w| format!("%{}%", w.to_lowercase())).collect()
}
// empty keyword list short-circuits BEFORE any SQL:
if keywords.is_empty() { return Ok(ChatRecallResults { results: vec![], total_matches: 0 }); }
```
SQL prefilter is followed by an authoritative Rust re-projection (`filter_for_audience(Role::Assistant)`), non-text blocks render as `[Tool: name]` / `[Thinking: …]`; totals recount agent-visible, non-turn-context rows per hit session; results sort by `Reverse(last_activity)`.

**Flow:** parse keywords → short-circuit on empty → one SQL pass (visibility + audience + OR-keywords + optional exclude/type/date filters + LIMIT) → group rows by session in Rust with audience re-filter → per-hit totals queries → sort by recency.
**Invariant:** Searchability uses the AGENT-visible axis (default-allow when metadata absent); turn-context rows are never searchable and never counted in totals; a user-only-audience text block inside an otherwise visible row cannot match. The LIMIT applies to matched MESSAGE rows, not sessions.
**Probe:** test `search_projects_audience_before_matching_and_limiting` (pins all three leak paths + the totals rule "session totals must not count turn-context or user-only rows") and `test_search_chat_history_preserves_message_limited_behavior`. Run: `cargo test -p goose --lib session::chat_history_search`. Contrast seam: list-side `message_keyword_clause` (session_manager.rs 362-385) matches USER-visible text via `instr` — different axis for a different consumer.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "goose", query: "ChatRecallResults search_chat_history execute fetch_rows process_rows session_totals convert_to_results", limit: 8, fields: ["lines"] });
```

## Verdict
Adopt: dual-layer visibility gating (cheap SQL prefilter + authoritative in-process projection), turn-context exclusion at both match and count time, message-level LIMIT semantics, empty-query short-circuit. Adapt block-renderer strings and metadata keys. Omit goose's SessionType plumbing.
