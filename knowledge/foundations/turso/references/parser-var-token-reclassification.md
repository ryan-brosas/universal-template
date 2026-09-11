<!-- capsule-v2 -->
# Parser variable-token reclassification — why is a bad parameter name just an "unrecognized token"?

**Source:** turso (Limbo) MIT `main@1654d1587`; Codebase Memory project `turso`. **Question:** When a `$`/`@`/`:` parameter's name is malformed, which error variant must the lexer emit and what message shape does SQLite compatibility demand?

## BadVariableName deleted; TK_ILLEGAL semantics via UnrecognizedToken
**Path/Symbol:** `sqlite/parser/src/lexer.rs`: `eat_var` (:843-861) routes non-`?` prefixes to `eat_named_var` (:863); rejection branch (:901-910) now constructs `Error::UnrecognizedToken` (was `BadVariableName`, variant DELETED from `sqlite/parser/src/error.rs` — enum now :6-45 without it) with comment citing SQLite's tokenizer (sqlite3GetToken, CC_VARALLEGAL ⇒ TK_ILLEGAL); display string `#[error("unrecognized token: \"{token_text}\"")]` (error.rs:9 — note quoted form, no offset); parser test pin :5516 inside `test_namespace_qualified_parameter_names` (:5484). Commit 2096a3b63.
**Signature:** `fn eat_named_var(&mut self, start: usize) -> Result<Token<'a>>`; error carries `(span, token_text, offset)` even though Display omits the offset.
**Data Shape:** name grammar = identifier bytes with a `::` pair legal anywhere (leading/middle/trailing — TCL `$ns::var`), zero identifier bytes or bad suffix byte ⇒ rejection.

### Decisive source
```rust
// sqlite/parser/src/lexer.rs:901-905:
if n_id == 0 || bad_suffix {
    // SQLite marks these TK_ILLEGAL and reports "unrecognized
    // token", not a variable-specific error.
    let token_text = String::from_utf8_lossy(&self.input[start..self.offset]).to_string();
    return Err(Error::UnrecognizedToken { span: ..., token_text, offset: start });
```

**Flow:** lexer sees `$`/`@`/`:` → eats identifier bytes (`::` pairs included) → n_id==0 (e.g. input `$a(b` stops at `(`... actually `$a(b` yields token text `$a(b`) or a bad suffix ⇒ UnrecognizedToken with the RAW text → parser aborts; users see `unrecognized token: "$a(b"` exactly as SQLite spells it. The dedicated variant existed only to add "at offset N" — dropped for byte-compatibility of messages.
**Invariant:** error-message text is API surface: conformance harnesses match SQLite's strings, so classify by TOKEN KIND (illegal character sequence), not by the lexical context that produced it. Deleting a variant beats deprecating it when no consumer matches on the enum shape.
**Probe:** from repo root: `grep -c 'BadVariableName' sqlite/parser/src/error.rs sqlite/parser/src/lexer.rs` → 0 per file (grep -c exits 1 on all-zero: expected); `grep -c 'unrecognized token: ' sqlite/parser/src/error.rs` → 1; runner pin: `sed -n '5516p' sqlite/parser/src/parser.rs` shows the assertion string verbatim.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "eat_named_var UnrecognizedToken", limit: 3 });
```
(resolves lexer fn nodes line-exact at this pin)

## Verdict
Adopt kind-based reclassification with SQLite-exact message spelling in any SQL dialect front-end; adapt to your host's i18n needs only if you own the harness too; omit the `::` namespace rule outside TCL-embedding contexts. Coverage caveat: none material.
