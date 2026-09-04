<!-- capsule-v2 -->
# Orphan-rule Format bridge — how do language-specific crates format syntax types owned by another crate?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** Rust's orphan rule forbids `impl Format<Context> for JsIfStatement` when both traits and type live in foreign crates — what is the indirection that makes per-node rules implementable downstream, and which blanket impls make the ergonomics work?

## The four-trait rule bridge
**Path/Symbol:** `crates/biome_formatter/src/lib.rs` — `Format<Context>` trait (:1338-1343, "the biome_formatter equivalent to std::fmt::Display"), `FormatRule<T>` (:1405-1410, has associated `Context`), `FormatRuleWithOptions<T>` (:1412-1417, `with_options(self, options) -> Self`), `FormatWithRule<Context>` (:1443-1449, `item() -> &Self::Item`), wrappers `FormatRefWithRule<'a,T,R>` (:1452-1500) and `FormatOwnedWithRule<T,R>` (:1502-1545).
**Signature:** `pub trait FormatRule<T> { type Context; fn fmt(&self, item: &T, f: &mut Formatter<Self::Context>) -> FormatResult<()>; }`.
**Data Shape:** a downstream crate defines a NEWTYPE (or rule struct) that owns the formatting logic for the foreign node type; the wrapper structs pair `(item, rule)` and implement `Format<R::Context>` by delegating to `rule.fmt(item, f)`.

### Decisive source
```rust
// lib.rs:1405-1410 — the doc comment IS the rationale:
/// Rule that knows how to format an object of type `T`.
///
/// Implementing [Format] on the object itself is preferred over implementing [FormatRule] but
/// this isn't possible inside of a dependent crate for external type.
///
/// For example, the `biome_js_formatter` crate isn't able to implement [Format] on `JsIfStatement`
/// because both the [Format] trait and `JsIfStatement` are external types (Rust's orphan rule).
///
/// That's why the `biome_js_formatter` crate must define a new-type that implements the
/// formatting of `JsIfStatement`.
pub trait FormatRule<T> {
    type Context;
    fn fmt(&self, item: &T, f: &mut Formatter<Self::Context>) -> FormatResult<()>;
}
```
```rust
// lib.rs:1774 (entry pipeline call site):
let format_node = FormatRefWithRule::new(&root, L::FormatRule::default());
```
Blanket impls on `Format` itself make everything compose without new impls per language: `&T where T: ?Sized + Format` (:1352), `&mut T` (:1361), `Option<T>` — None formats as nothing (:1371-1380), `SyntaxResult<T>` — errors convert via `.into()` (:1382-1390), and `()` — intentionally empty (:1392-1398).
**Flow:** language crate defines `impl FormatRule<JsIfStatement> for FormatJsIfStatement { type Context = JsFormatContext }` → nodes expose `AsFormat`/`IntoFormat` returning the newtype → callers write `write!(f, [node.format()])`; the entry pipeline constructs `FormatRefWithRule(root, L::FormatRule::default())` so ONE default rule drives whole-tree dispatch. `with_options` rewraps the rule value before formatting (`FormatRefWithRule::with_options` :1484, owned twin :1526); `FormatOwnedWithRule::with_item/into_item` allow re-targeting the wrapped node after construction.
**Invariant:** `Format` is implemented ONCE generically over all hosts; every language-specific customization flows through `FormatRule`'s associated `Context`, which is why `Formatter<Self::Context>` inside a rule can access language options/comments while generic code cannot. A porter who tries to add per-language methods to `Formatter` instead of an associated-context trait couples the kernel to one language.
**Probe:** `grep -c "Rust's orphan rule" crates/biome_formatter/src/lib.rs` → 2 (trait doc + FormatWithRule doc); `grep -n 'FormatRefWithRule::new' crates/biome_formatter/src/lib.rs` → :1774+:1850; direct tests in `format_extensions.rs` use exactly this bridge (`FormatRefWithRule::new(&item, TestRule{..}).with_scoped_options(..)`, 4-test mod incl. `scoped_options_nest_in_lifo_order` :403).
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"biome","name_pattern":"FormatScopedOptions"}'
# biome.crates.biome_formatter.src.format_extensions FormatScopedOptions Interface 17-26 / FormatScopedOptionsExt Interface 63-86
```

## Verdict
Adopt the FormatRule/newtype bridge verbatim for any host with an orphan-rule constraint (it maps directly to trait-object or free-function dispatch in non-Rust hosts); adapt `FormatRuleWithOptions` into your option-passing idiom; omit the `&T/&mut T/Option/SyntaxResult/()` blanket impls only if your language lacks their analogues. Coverage: no_recorded_issue on format_extensions.rs; lib.rs production ranges fully indexed.
