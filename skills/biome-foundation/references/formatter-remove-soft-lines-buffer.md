<!-- capsule-v2 -->
# RemoveSoftLinesBuffer — how does best_fitting measure variants without re-running rule code, and what exactly gets stripped?

**Source:** biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** The printer must simulate "infinite print width" to flat-measure best_fitting variants and fill items — which buffer does that and what is its exact transformation contract over interned elements?

## Strip filter + memoized interned cleaning
**Path/Symbol:** `crates/biome_formatter/src/buffer.rs:491-535` (struct, `new`, `clean_interned`, `is_in_expanded_conditional_content`), `buffer.rs:537-632` (free fn `clean_interned`), `buffer.rs:633-712` (Buffer impl `write_element`).
**Signature:** `RemoveSoftLinesBuffer::new(inner: &'a mut dyn Buffer<Context = Context>) -> Self`; state = `interned_cache: FxHashMap<Interned, Interned>` + `conditional_content_stack: Vec<Condition>`.
**Data Shape:** wrapper implementing `Buffer`; per element decides DROP / REWRITE / PASS-THROUGH while maintaining two pieces of context (condition stack; interned→cleaned memo).

### Decisive source
```rust
// buffer.rs:653-674 — the five-rule strip ladder
match element {
    FormatElement::Tag(Tag::StartConditionalContent(condition)) => {
        self.conditional_content_stack.push(condition.clone());
    }
    FormatElement::Tag(Tag::EndConditionalContent) => { self.conditional_content_stack.pop(); }
    // All content within an expanded conditional gets dropped. If there's a
    // matching flat variant, that will still get kept.
    _ if self.is_in_expanded_conditional_content() => {}
    FormatElement::Line(LineMode::Soft) => {}
    FormatElement::Line(LineMode::SoftOrSpace) => {
        self.inner.write_element(FormatElement::Space)?
    }
    FormatElement::Interned(interned) => {
        let cleaned = self.clean_interned(&interned);
        self.inner.write_element(FormatElement::Interned(cleaned))?
    }
    // Since this buffer aims to simulate infinite print width, we don't need to retain the best fitting.
    // Just extract the flattest variant and then handle elements within it.
    FormatElement::BestFitting(best_fitting) => {
        let most_flat = best_fitting.most_flat();          // format_element.rs:493
        most_flat.iter().rev()
            .for_each(|element| element_statck.push(element.clone()));
    }
    element => self.inner.write_element(element)?,
}
```

**Flow:** `best_fitting`'s measurement pass routes writes through this buffer → soft lines vanish, SoftOrSpace becomes Space, expanded-only conditional content disappears wholesale (stack-tracked), nested BestFitting dissolves into its flattest variant recursively, interned subtrees are cleaned ONCE per distinct element and cached (`FxHashMap<Interned, Interned>`) since `Interned` is hash-addressable by content.
**Invariants:** (1) The cache is intentionally NOT snapshotted ("worst that can happen is that it holds on interned elements that are now unused", :496-501) — safe because keys are immutable interned documents. (2) Expanded-conditionals drop rule needs the STACK, not a boolean: nested conditionals must restore correctly on EndConditionalContent. (3) `most_flat()` lives on `BestFittingVariants` (format_element.rs:493) — the buffer never re-runs user Format code, it only transforms already-written elements. (4) Free function extracted from the method "to avoid monomorphization" (:536) — keep the split when porting generics-heavy hosts.
**Probe:** `grep -c 'FxHashMap<Interned, Interned>' crates/biome_formatter/src/buffer.rs` → `2`; `grep -c 'best_fitting.most_flat()' crates/biome_formatter/src/buffer.rs` → `2`; `grep -n 'pub fn most_flat' crates/biome_formatter/src/format_element.rs` → `493:`.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"biome","query":"RemoveSoftLinesBuffer clean_interned","limit":8,"detail":"ids"}'
```
Resolves `RemoveSoftLinesBuffer.new Method buffer.rs 509-515` plus sibling methods line-exact (13 total nodes).

## Verdict
Adopt the five-rule ladder and memoized interning; adapt Interned identity (content-hash set) and Condition stack to host IR. This buffer is the reason `best_fitting!` docs call measurement cheap-ish — omitting it forces printers to re-execute rule code per variant, the classic wrong port. Direct test: `interned_best_fitting_allows_sibling_expand_propagation` (format_element/document.rs:993) pins interning × best_fitting interaction.
