<!-- capsule-v2 -->
# Memoized + scoped-options format extensions — how do you format an expensive subtree twice without computing it twice, and how do you temporarily override context options without leaking them?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** `if_group_breaks`/`if_group_fits` can force the same subtree through the printer twice, and rules need temporary option overrides — what are the two extension kernels in `format_extensions.rs`, and what does the error path guarantee?

## OnceCell memoization + enter/exit context scoping
**Path/Symbol:** `crates/biome_formatter/src/format_extensions.rs` (440L) — `MemoizeFormat<Context>::memoized()` (:95-152, doc example pins observable behavior: unmemoized prints "Formatted 1 times. Formatted 2 times.", memoized prints "Formatted 3 times. Formatted 3 times." :130-137); `Memoized<F,C> { inner, memory: OnceCell<FormatResult<Option<FormatElement>>> }` (:156-160); `inspect(&mut self, f)` (:230-244, returns `&[FormatElement]` for will_break probing); `Format::fmt` writes via `f.write_element(elements.clone())` (element CLONE = pointer-interned handle, not deep copy). Scoped plane: `FormatScopedOptions<Context, Item>` trait (:17-26, `type Restore` + `enter`/`exit`), `FormatWithScopedOptions` wrapper (:30-56), blanket ext trait `FormatScopedOptionsExt::with_scoped_options` (:63-86).
**Signature:** `fn with_scoped_options<Options>(self, options: Options) -> FormatWithScopedOptions<Self, Options> where Self: FormatWithRule<Context>, Options: FormatScopedOptions<Context, Self::Item>`.
**Data Shape:** memo cache stores the RESULT OF FORMATTING including errors (`FormatResult<Option<FormatElement>>`) — an erroring subtree memoizes its error and replays it on every subsequent use. Scoped state is whatever `Restore` carries; the test uses the previous enum value.

### Decisive source
```rust
// format_extensions.rs:39-44 — exit runs even when formatting returned Err:
impl … Format<Context> for FormatWithScopedOptions<Formatted, Options> {
    #[inline(always)]
    fn fmt(&self, f: &mut Formatter<Context>) -> FormatResult<()> {
        let restore = self.options.enter(self.formatted.item(), f.context_mut());
        let result = self.formatted.fmt(f);
        self.options.exit(restore, f.context_mut());   // NOT ?-short-circuited
        result
    }
}
```
Trait contract (:8-11): "Implementations must return enough state from `Self::enter` for `Self::exit` to restore the context, **including when formatting returns an error**."
**Flow (scoped):** wrap any existing `FormatWithRule` WITHOUT replacing its rule (generated node unions keep their dispatch; rule-owned options should prefer `FormatRuleWithOptions` instead — doc :60-62). Chained scopes NEST: first scope in the chain is closest to the item and wins on shared state (LIFO restore). **Flow (memo):** first `fmt`/`inspect` call runs `f.intern(&self.inner)` inside `get_or_init`; later calls clone the cached element handle. `inspect` lets a caller check `will_break()` BEFORE deciding to print flat vs broken, then re-print from cache.
**Invariant:** the error-path restore is the whole point of the enter/exit split — a porter who writes `self.formatted.fmt(f)?;` before `exit()` leaks overridden context into every SIBLING formatted after a failing rule. The four-test mod proves it directly (`scoped_options_restore_context_after_an_error` :424 asserts observed mode returns to Outer AND the error still propagates as `Err(FormatError::SyntaxError)`), plus copyability (`scoped_options_copy_does_not_depend_on_context` :386) and nesting (:403).
**Probe:** `grep -c 'get_or_init' crates/biome_formatter/src/format_extensions.rs` → 2; `grep -c 'f.intern(&self.inner)' …` → 2; `grep -n 'fn exit(&self, restore: Self::Restore, context: &mut Context)' …` → :25; `grep -n 'scoped_options_restore_context_after_an_error' …` → :424; `grep -c '#\[test\]' …` → 4.
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"biome","name_pattern":"Memoized","limit":5}'
# Memoized Struct 156-160 + memoized Method 144-149 (format_extensions)
codebase-memory-mcp cli search_graph '{"project":"biome","name_pattern":"FormatScopedOptions"}'
# FormatScopedOptions Interface 17-26 / Ext 63-86
```

## Verdict
Adopt both kernels: memoization for fits-probing double-print economics (pairs with formatter-ir.md interning), scoped options for any rule that must temporarily flip context state; adapt `OnceCell` to your host's once-lazy primitive (JS: a lazily-assigned field; the FormatResult-in-cache semantics matter more than the cell); omit `inspect` if your printer exposes group-break decisions differently. Coverage: file fully indexed no_recorded_issue @ generation 2026-08-16T00:20:04Z.
