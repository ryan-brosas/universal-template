<!-- capsule-v2 -->
# Speculative parsing flag + try_parse — why must error recovery be silenced during a speculative parse?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How does the parser stop speculative parses from consuming tokens or emitting diagnostics that would poison the real parse?

## state.speculative_parsing + try_parse
**Path/Symbol:** `crates/biome_js_parser/src/state.rs:JsParserState.speculative_parsing` (:98-109), `crates/biome_js_parser/src/parser.rs:JsParser::is_speculative_parsing` (:171-173), `crates/biome_js_parser/src/syntax/typescript.rs:try_parse` (:127-142).
**Signature:** `pub(crate) fn try_parse<T, E>(p: &mut JsParser, func: impl FnOnce(&mut JsParser) -> Result<T, E>) -> Result<T, E>`
**Data Shape:** `speculative_parsing: bool` on parser state (unscoped — deliberately NOT part of any reset mask); `try_parse` returns the closure's `Result`, rewinding the whole `JsParserCheckpoint` on `Err`.

### Decisive source
```rust
pub(crate) fn try_parse<T, E>(p: &mut JsParser, func: impl FnOnce(&mut JsParser) -> Result<T, E>) -> Result<T, E> {
    let checkpoint = p.checkpoint();
    let old_value = std::mem::replace(&mut p.state_mut().speculative_parsing, true);
    let res = func(p);
    p.state_mut().speculative_parsing = old_value;
    if res.is_err() { p.rewind(checkpoint); }
    res
}
```
And the motivating doc comment from state.rs:
> "the parser isn't allowed to skip any tokens while doing error recovery because it may then successfully skip over all invalid tokens, so that it appears as if it was able to parse the syntax correctly."

**Flow:** enter speculation → flip flag (saving old) → run probe → restore flag → rewind events+tokens+state iff `Err`. While flagged: recovery helpers refuse to skip tokens (`SingleTokenParseRecovery::recover` returns early; deprecated but the contract survives in `ParseRecoveryTokenSet` usage), diagnostics are still *recorded* but the whole event stream is discarded on failure.
**Invariant:** The flag is restored even on success and nested speculation restores the *outer* value, not `false` — always swap-and-restore (`mem::replace`), never assign. A speculative success path must leave zero net token movement only via checkpoint rewind; anything consumed before the flag was set stays consumed.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/ok/ts/ts_arrow_function_type_parameters.ts` (`<A, B extends A, C = string>(a: A, b: B) => "hello"` speculates as arrow through type parameters) vs `ok/jsx/jsx_type_arguments.js`-style `<A extends>() =</A>` cases where JSX wins because speculation fails cleanly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "try_parse speculative_parsing checkpoint rewind", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the boolean speculation gate + swap-restore wrapper as the minimal speculative-parsing kit; adapt which recovery operations it silences; omit the deprecated `SingleTokenParseRecovery` struct itself (upstream marks it `Use ParsedSyntax with ParseRecovery instead`) while keeping its early-return-on-speculation behavior.
