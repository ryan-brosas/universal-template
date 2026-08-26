<!-- capsule-v2 -->
# token() debug asserts — what two input preconditions does the cheapest IR builder enforce and why must text be 'static ASCII?

**Source:** biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** A porter copying `token("...")` into a hot formatting path needs to know which inputs are ILLEGAL even though the signature accepts them.

## Token struct + constructor guards
**Path/Symbol:** `crates/biome_formatter/src/builders.rs:272-292` (`token()` + `Token` + `Format::fmt`), `builders.rs:294-298` (Debug).
**Signature:** `pub fn token(text: &'static str) -> Token`; `Token { text: &'static str }` (Copy); `fmt` writes `FormatElement::Token { text: self.text }` directly.
**Data Shape:** zero-cost newtype over a string literal; NO runtime validation — both rules are `debug_assert!`, free in release builds.

### Decisive source
```rust
// builders.rs:273-281
pub fn token(text: &'static str) -> Token {
    debug_assert!(text.is_ascii(), "Token must be ASCII text only");
    debug_assert!(
        !text.contains(['\n', '\r', '\t']),
        "A token should not contain any newlines or tab characters"
    );
    Token { text }
}
```

**Flow:** rule code writes punctuation/keywords via `token("...")` → element lands in IR verbatim → printer copies bytes with no escaping pass. Non-ASCII or whitespace-bearing text must go through `text(&str, Option<TextSize>)` (:363) or `located_token_text` / `syntax_token_cow_slice` (:404) which carry source positions/widths instead.
**Invariants:** (1) Tokens are for PUNCTUATION and fixed keywords only — the printer assumes single-line width-measurable fragments. (2) `'static` lifetime is load-bearing: elements hold the reference without ownership; porting to a host without static promotion requires interning. (3) Violations surface ONLY in debug builds — a release-mode formatter will happily print tabs inside "tokens" and corrupt alignment measurement.
**Probe:** `grep -n 'debug_assert!(text.is_ascii()' crates/biome_formatter/src/builders.rs` → `274:`; `grep -n "text.contains(\['\\\\n', '\\\\r', '\\\\t'\])" crates/biome_formatter/src/builders.rs` → `276:` (or `sed -n '276p'` shows the contains line).

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"biome","query":"Token text ascii","limit":5,"detail":"ids"}'
```
Resolves `builders.Token` cluster; note heavy name collision with syntax tokens — filter by file.

## Verdict
Adopt the assert pair plus the escape hatch hierarchy (token → text → located/cow variants by increasing fidelity); adapt to host string types. Direct tests: doc examples :246-270 pin output including the escaped-tab literal case.
