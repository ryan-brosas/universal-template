<!-- capsule-v2 -->
# Formatting and naming — does code pass rustfmt and RFC 430 casing?

**Source:** Rust Style Guide; API guidelines C-CASE, C-CONV. **Question:** Will `cargo fmt` and naming conventions match ecosystem expectations?

## Format seam
**Path/Symbol:** `*.rs` sources, `Cargo.toml`.
**Signature:** `rustfmt` default style; 4-space block indent; 100-column limit.
**Data Shape:** trailing commas in multiline lists.

### Decisive pattern
```rust
fn process(
    input: &str,
    options: Options,
) -> Result<Output, ProcessError> {
    let value = if input.is_empty() {
        default_value()
    } else {
        parse(input)?
    };
    Ok(transform(value, options))
}
```

**Flow:** write idiomatic Rust → `cargo fmt` → prefer block indent over visual alignment.
**Invariant:** mechanical formatting is **rustfmt's job** — CI runs `cargo fmt --check`.
**Probe:** fmt check clean; no manual column alignment fighting formatter.

## Naming seam
```rust
struct HttpServer;
const MAX_RETRIES: u32 = 3;

impl Buffer {
    pub fn as_slice(&self) -> &[u8] { ... }
    pub fn into_inner(self) -> Vec<u8> { ... }
}
```

**Flow:** pick RFC 430 case per item kind → conversion prefix signals cost (`as_`/`to_`/`into_`) → avoid stutter and `get_` prefixes on ordinary getters.
**Invariant:** acronyms in types are one word (`Uuid`); snake_case uses full words (`btree_map` not `b_tree_map` except trailing single letter like `PI_2`).
**Probe:** clippy `wrong_self_convention` / review catches `get_foo` getters; no `-rs` crate suffix.

## Verdict
Adopt rustfmt defaults + RFC 430 naming + conversion prefixes. Learning note: `rust-style-learning-note.md`.
