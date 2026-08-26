<!-- capsule-v2 -->
# best_fitting! macro contract — what must a porter guarantee about variant count and ordering before the printer ever sees the element?

**Source:** biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** `BestFitting::from_arguments_unchecked` is deliberately not `unsafe` yet relies on a runtime invariant the type system can't see — which invariant, who enforces it, and what ordering do variants carry?

## Unchecked constructor + macro head/tail split
**Path/Symbol:** `crates/biome_formatter/src/builders.rs:2916-2946` (`BestFitting` struct + `from_arguments_unchecked`), `crates/biome_formatter/src/macros.rs:330-334` (`best_fitting!`).
**Signature:** `pub fn from_arguments_unchecked(variants: Arguments<'a, Context>) -> Self` (asserts `variants.0.len() >= 2`); `best_fitting!($least_expanded:expr, $($tail:expr),+) => BestFitting::from_arguments_unchecked(format_args!($least_expanded, $($tail),+))`.
**Data Shape:** N ≥ 2 `Format<Context>` variants packed into one `Arguments` slice; first = most flat (fits widest), last = most expanded (last resort). `BestFitting::fmt` re-wraps each variant in `StartBestFittingEntry`/`EndBestFittingEntry` tags in a scratch `VecBuffer` and emits one `FormatElement::BestFitting(BestFittingVariants::from_vec_unchecked(...))`.

### Decisive source
```rust
// builders.rs:2924-2945 — doc-comment IS the porting spec
/// The method itself isn't unsafe but it is to discourage people from using it because
/// the printer will panic if the slice doesn't contain at least the least and most
/// expanded variants. ... As we can't place tail expressions in a block for temporary
/// lifetime extension since Rust 2024, we can't use an `unsafe` block in the macro.
pub fn from_arguments_unchecked(variants: Arguments<'a, Context>) -> Self {
    assert!(
        variants.0.len() >= 2,
        "Requires at least the least expanded and most expanded variants"
    );
    Self { variants }
}
```

**Flow:** `best_fitting![a, b, c]` → macro packs all three via `format_args!` → constructor asserts len ≥ 2 → `fmt` buffers each variant behind entry tags → printer measures every variant except the last in Flat mode and prints the first that fits, else prints the LAST variant in Expanded mode (macros.rs docs :148-151, :314-320).
**Invariant:** (1) At least TWO variants — the assert is the only guard; bypassing the macro with an empty/one-element Arguments panics at format time, not compile time. (2) Order IS semantics: least-expanded FIRST, most-expanded LAST — reversing produces wrong output silently. (3) `from_vec_unchecked` on the element side (builders.rs:2960-2964 SAFETY comment) trusts the same ≥2 guarantee.
**Probe:** `grep -n 'variants.0.len() >= 2' crates/biome_formatter/src/builders.rs` → `2940:`; `grep -c 'from_arguments_unchecked' crates/biome_formatter/src/builders.rs crates/biome_formatter/src/macros.rs` → `1` + `1` (definition + sole macro caller — nothing else may call it); `grep -c 'from_vec_unchecked' crates/biome_formatter/src/builders.rs` → `2`.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"biome","query":"BestFitting from_arguments_unchecked variants","limit":6,"detail":"ids"}'
```
Resolves `biome.crates.biome_formatter.src.builders.BestFitting.*` line-exact. Caveat: enum VALUE `StartBestFittingEntry` is not an indexed symbol (recurred pass-11 finding) — cite the Struct/Method nodes.

## Verdict
Adopt the assert-guarded unchecked-constructor pattern (cheap runtime invariant instead of unsafe) and the flat-first/expanded-last ordering contract; adapt the Rust-2024 temporary-lifetime rationale to your host's closure rules. Real consumers: jsx child_list.rs, jsx tag/element.rs, ts type_assertion_expression.rs, member_chain — every one passes 2–3 hand-ordered variants. Complexity warning travels with the port: nested best_fitting is quadratic in the printer (macros.rs:307-312).
