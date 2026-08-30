<!-- capsule-v2 -->
# Import format sniffing + normalize-to-native dispatch — how do you accept four transcript dialects through one import pipeline without misclassification?

**Source:** goose Apache-2.0 `main@2eb3ab1001dedb5ab09a6ed60158adfc248bac56`; Codebase Memory `goose`. **Question:** How do I detect which agent exported a session payload (native / Claude Code / Codex / Pi) and convert it to my native shape so one battle-tested import path handles all of them?

## Sniff ladder + dispatch plane
**Path/Symbol:** `crates/goose/src/session/import_formats/mod.rs` : `detect_format` (93–147), `convert_to_goose_session_json` (150–157), `nest_legacy_token_fields` (171–211), `build_session_json` (39–70); consumer `SessionStorage.import_session` (`session_manager.rs` 2342–2382).
**Signature:** `pub fn detect_format(content: &str) -> ImportFormat` / `pub fn convert_to_goose_session_json(content: &str) -> Result<String>` / `async fn import_session(&self, session_manager: &SessionManager, json: &str, session_type_override: Option<SessionType>) -> Result<Session>`.
**Data Shape:** `ImportFormat { Goose, ClaudeCode, Codex, Pi }`; converters return a serialized native `Session` JSON string; `ImportedSession<'a>` carries harvested session-level fields (id/working_dir/name/timestamps/usage/cost/conversation).

### Decisive source
```rust
let first_line = content.lines().find(|l| !l.trim().is_empty()).unwrap_or("");
if let Ok(v) = serde_json::from_str::<Value>(first_line) {
    if v.get("type").and_then(|t| t.as_str()) == Some("session_meta") { return ImportFormat::Codex; }
    if v.get("type")... == Some("session")
        && (v.get("version").is_some() || (v.get("cwd").is_some() && v.get("id").is_some())) {
        return ImportFormat::Pi;                       // header line decides
    }
    if v.is_object() && v.get("sessionId").is_some()
        && (v.get("type").is_some() || v.get("uuid").is_some()) {
        return ImportFormat::ClaudeCode;               // per-line JSONL w/ sessionId
    }
}
// whole-payload parse containing working_dir|workingDir → Goose;
// fallback rescans first 5 non-blank lines for any sessionId → ClaudeCode;
// default → Goose.
```

**Flow:** sniff first non-blank line → dispatch on `ImportFormat` (foreign formats via dedicated converters; native Goose path runs `upgrade_legacy_token_fields`) → `import_session` normalizes, deserializes into the native Session, creates a FRESH date-sequential session id, applies metadata through the update builder (`user_provided_name` only when the import says `user_set_name`), `replace_conversation`, re-reads with messages.
**Invariant:** Sniffing never trusts later lines when the first line decides; every foreign payload becomes the FULL native JSON shape before storage (`build_session_json` emits `user_set_name:false`, `session_type:"user"`, and mirrors harvested usage into BOTH `usage` and `accumulated_usage`); legacy flat token fields fold into nested objects ONLY when those keys are absent, renaming `cache_read_tokens→cache_read_input_tokens` (+write twin). Imports always mint new IDs — they never resurrect the source id.
**Probe:** `cargo test -p goose --lib session::import_formats` (round-trip fixtures per format); storage-side `test_export_import_roundtrip` pins the native path. Run: `cargo test -p goose --lib session::`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "goose", query: "detect format sniff import convert goose session json legacy token fields normalize", limit: 10, fields: ["signature", "lines"] });
// executed live this pass: top hits nest_legacy_token_fields 161-211, detect_format 93-147,
// convert_to_goose_session_json 150-157, build_session_json 39-70
```

## Verdict
Adopt: first-line sniff ladder with whole-payload + bounded-rescan fallbacks, normalize-everything-to-native-JSON before the single import entry point, fresh-ID-on-import, absent-key-only legacy field folding. Adapt the format markers to your ecosystem. Omit the three foreign converter interiors (claude_code/codex/pi) unless you need their exact grammars. Coverage caveat: converter interiors were not studied this pass (recorded omission); mod.rs itself fully indexed (no_recorded_issue).
