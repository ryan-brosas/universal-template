<!-- capsule-v2 -->
# Session auto-naming ladder — when should a session be renamed, and how do you extract a title from an LLM answer?

**Source:** goose Apache-2.0 `main@2eb3ab1001dedb5ab09a6ed60158adfc248bac56`; Codebase Memory `goose`. **Question:** How do I auto-title sessions without ever clobbering user names, and turn a chatty model response into a ≤100-char title?

## Naming gate + extraction ladder
**Path/Symbol:** `crates/goose/src/session/session_manager.rs` : `SessionManager.maybe_update_name` (560-621); `crates/goose/src/session/session_naming.rs` : `strip_xml_tags` (11-19), `extract_short_title` (21-71), `get_initial_user_messages`/`get_preprompt_context` (75-109), `generate_session_name` (113-178).
**Signature:** `pub async fn maybe_update_name(&self, id: &str, provider: Arc<dyn Provider>) -> Result<Option<SessionNameUpdate>>`; `pub(crate) async fn generate_session_name(provider: &dyn Provider, model_config: &ModelConfig, session_id: &str, messages: &Conversation) -> Result<String>`.
**Data Shape:** `MSG_COUNT_FOR_SESSION_NAME_GENERATION: usize = 3`; writes go through `system_generated_name_update` → update builder `.system_generated_name()` which sets `user_set_name=false`; empty trimmed names are dropped by the builder itself.

### Decisive source
```rust
if session.user_set_name { return Ok(None); }
if session.session_type == SessionType::Scheduled { return Ok(None); }
if let Some(recipe) = &session.recipe {
    let name = recipe.title.trim().to_string();
    if name.is_empty() || session.name == name { return Ok(None); }
    return Ok(Some(self.system_generated_name_update(id, name).await?));
}
...
let should_generate_name = if provider.manages_own_context() {
    user_message_count == 1
} else {
    user_message_count <= MSG_COUNT_FOR_SESSION_NAME_GENERATION
};
```
```rust
// extract_short_title fallback order for >8-word answers:
//   1. LAST quoted span of 2..=8 words ("..." | '...' | `...`, quote must not follow alnum)
if let Some(title) = results.last() { return title.clone(); }
//   2. last non-empty line
if let Some(last) = text.lines().rev().find(|l| !l.trim().is_empty()) { return last.trim().to_string(); }
```
Cleanup before extraction: `strip_xml_tags` (block regex `<tag…>…</tag>` then bare-tag regex) + whitespace collapse; final `safe_truncate(..., 100)`.

**Flow:** eligibility gate (user-named? scheduled? recipe-titled?) → count user-visible user messages → maybe generate (prompt = fenced BACKGROUND-CONTEXT preprompt section + BEGIN/END markers around first ≤3 visible user messages + suffix instruction; stateful providers use a simple one-shot description call, others complete_fast with the session_name.md template as system prompt) → strip tags/collapse → extract short title → truncate to 100 → apply as system-generated rename.
**Invariant:** A user-set name is never overwritten; Scheduled sessions are never renamed; renames always carry `user_set_name=false` so they remain eligible for future replacement only via the same ladder.
**Probe:** tests `test_maybe_update_name_preserves_user_renamed_session`, `..._preserves_scheduled_session`, `..._uses_recipe_title_for_recipe_session`, `..._uses_local_name_for_stateful_provider`, `..._updates_eligible_session` plus pure tests `test_strip_xml_tags` (unicode/self-closing/orphan tags), `test_extract_short_title` (last-quote-wins, line fallback). Run: `cargo test -p goose --lib session::session_naming`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "goose", query: "maybe_update_name generate_session_name extract_short_title strip_xml_tags safe_truncate recipe title", limit: 8, fields: ["lines"] });
```

## Verdict
Adopt: the gate order (user-name → session-kind → recipe → message-count trigger) and the three-stage answer-extraction heuristic with quote-span preference. Adapt prompt templates and provider dispatch. Omit goose's Provider trait coupling and recipe type.
