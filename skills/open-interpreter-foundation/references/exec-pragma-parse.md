<!-- capsule-v2 -->
# exec-pragma-parse — how does one tool call carry per-call knobs without a schema?

**Source:** open-interpreter Apache-2.0 `main@5b07159c477920c159d8892d112b480e7307f257`; Codebase Memory `ext-open-interpreter`. **Question:** How are `yield_time_ms` / `max_output_tokens` smuggled inside raw JS source, and what must fail vs pass?

## parse_exec_source first-line pragma
**Path/Symbol:** `codex-rs/code-mode-protocol/src/description.rs` : `parse_exec_source` (:167-249), `CodeModeExecPragma` (:151-158, `#[serde(deny_unknown_fields)]`), `CODE_MODE_PRAGMA_PREFIX = "// @exec:"` (:126).
**Signature:** `fn parse_exec_source(input: &str) -> Result<ParsedExecSource, String>` where `ParsedExecSource { code: String, yield_time_ms: Option<u64>, max_output_tokens: Option<usize> }`.
**Data Shape:** ONLY the first line is inspected (`splitn(2,'\n')`); the pragma JSON allows exactly two keys; both bounded by `MAX_JS_SAFE_INTEGER = 2^53-1`.

### Decisive source
```rust
let Some(pragma) = trimmed.strip_prefix(CODE_MODE_PRAGMA_PREFIX) else {
    return Ok(args);                       // no pragma => whole input IS the code
};
if rest.trim().is_empty() {
    return Err("exec pragma must be followed by JavaScript source on subsequent lines");
}
...
for key in object.keys() {
    match key.as_str() {
        "yield_time_ms" | "max_output_tokens" => {}
        _ => return Err(format!("exec pragma only supports ...; got `{key}`")),
    }
}
```

**Flow:** empty input → error (never treated as code) → first-line prefix check → require non-empty remainder → parse directive as JSON object → reject unknown keys → serde-typed parse with safe-integer bounds → strip line 1 from code.
**Invariant:** The pragma is stripped from `code` before evaluation — a porter who leaves it in feeds `// @exec:...` to V8 as a harmless comment but loses the knob values. Unknown-key rejection happens BEFORE typed parsing so the error names the offending key. The grammar in `execute_spec.rs` (`pragma_source: PRAGMA_LINE NEWLINE SOURCE`) mirrors this exactly for provider-side constrained decoding.
**Probe:** in-file tests `parse_exec_source_without_pragma`, `parse_exec_source_with_pragma` pin both polarities at the pinned commit.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-interpreter", query: "parse_exec_source CODE_MODE_PRAGMA_PREFIX", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt first-line-only parsing with deny-unknown-fields and safe-integer clamps; adopt the matching freeform grammar so providers that support constrained decoding emit valid sources. Omit the exact error strings.
