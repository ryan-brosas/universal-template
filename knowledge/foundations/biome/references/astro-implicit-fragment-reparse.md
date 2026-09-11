<!-- capsule-v2 -->
# Astro implicit-fragment checkpoint/rewind reparse — how does a parser add a dialect-gated "adjacent tags = fragment" rule to an existing JSX production without breaking JSX, and why must the first tag be parsed twice?

**Source:** Biome MIT `main@88f805e19b67ab4c876e4fc4a8b4018bd03df20b`; Codebase Memory project `biome` (refreshed in place 2026-08-24, 143,356 nodes / 652,625 edges). **Question:** How do you teach an existing tag-expression parser that `<p>a</p><div />` is one delimiter-less fragment in Astro but stays two invalid-in-JSX statements — without forking the JSX grammar?

## parse_jsx_tag_expression speculative completion
**Path/Symbol:** `crates/biome_js_parser/src/syntax/jsx/mod.rs:parse_jsx_tag_expression` (:53-79), `is_at_astro_adjacent_sibling` (:83-85), `is_at_jsx_tag_start` (:87-92), `AstroImplicitFragmentChildren` (:94-113), `parse_astro_implicit_fragment` (:120-128); feature gate `JsSyntaxFeature::Astro.is_supported` (biome_js_parser/src/lib.rs:108 → `as_embedding_kind().is_astro()`).
**Signature:** `fn parse_jsx_tag_expression(p: &mut JsParser) -> ParsedSyntax`; `fn is_at_jsx_tag_start(p: &mut JsParser) -> bool`.
**Data Shape:** After parsing one complete tag via `parse_any_jsx_tag`, if `Astro.is_supported(p) && is_at_jsx_tag_start(p)` then the marker just completed (`JSX_TAG_EXPRESSION`) is ABANDONED (not completed!), the parser rewinds to the checkpoint taken BEFORE the first tag, and the whole thing reparses as `JSX_TAG_EXPRESSION { ASTRO_IMPLICIT_FRAGMENT { JSX_CHILD_LIST of parse_any_jsx_tag elements } }`.

### Decisive source
```rust
let checkpoint = p.checkpoint();
let m = p.start();

// Safety: Safe because `parse_any_jsx_tag only returns Absent if the parser isn't positioned
// at the `<` token which is tested for at the beginning of the function.
parse_any_jsx_tag(p, true).unwrap();

if is_at_astro_adjacent_sibling(p) {
    m.abandon(p);                    // discard the single-tag marker entirely
    p.rewind(checkpoint);            // token cursor + events back to before `<`
    return parse_astro_implicit_fragment(p);   // reparse ALL siblings under one node
}

Present(m.complete(p, JSX_TAG_EXPRESSION))
```
```rust
struct AstroImplicitFragmentChildren;
impl ParseNodeList for AstroImplicitFragmentChildren {
    type Kind = JsSyntaxKind;
    const LIST_KIND: Self::Kind = JsSyntaxKind::JSX_CHILD_LIST;
    fn parse_element(&mut self, p: &mut JsParser) -> ParsedSyntax {
        parse_any_jsx_tag(p, true)
    }
    fn is_at_list_end(&self, p: &mut JsParser) -> bool {
        !is_at_jsx_tag_start(p)
    }
    // JS_BOGUS recovery with [<, >, {, ] token set, jsx_expected_children
}
```

## Flow
1. Entry gate unchanged (`<` + `>`|ident|metavariable lookahead) — JSX-vs-assertion decision is untouched.
2. Parse the first tag normally (speculatively — its result is provisional).
3. Look ahead: another tag start immediately after ⇒ this was never a plain tag expression.
4. `m.abandon(p)` + `p.rewind(checkpoint)` — the event stream and token cursor are rolled back; nothing partial leaks into the final tree.
5. Reparse under `AstroImplicitFragmentChildren.parse_list`: each element is a full `parse_any_jsx_tag(p, true)` (elements can carry attributes/children), list ends at any non-tag-start.
6. Wrap: inner `ASTRO_IMPLICIT_FRAGMENT` marker inside outer `JSX_TAG_EXPRESSION` — downstream consumers keep matching `JsxTagExpression.tag`.

## Invariant
- **The rewind is the correctness kernel:** you cannot "complete then convert" because the first tag's children/events were emitted under the wrong parent marker. Abandon + rewind + full reparse is the only lossless path. A port that completes-then-wraps produces double-parsed children or orphaned events.
- The probe order matters: sibling check runs ONLY after the first tag parsed successfully (`.unwrap()` safety comment documents why it cannot be Absent there).
- Dialect gate lives in ONE predicate: `Astro.is_supported(p)` reads `source_type().as_embedding_kind().is_astro()` — the grammar change is invisible to plain JSX/TSX files (fixture `jsx_missing_closing_fragment.jsx.snap` proves adjacent `<p>a</p>\n<div />` still parses as separate JsxElement children of a JsxFragment in JSX mode, with the SAME error count as before).
- `AstroImplicitFragment` slots: exactly ONE child slot (the JsxChildList); the generated syntax_factory demotes to bogus on extra children.

## Probe (direct tests)
From repo root:
- `grep -c 'is_at_astro_adjacent_sibling\|is_at_jsx_tag_start' crates/biome_js_parser/src/syntax/jsx/mod.rs` → **5** (2 defs + call sites + doc comment).
- Snapshot AST proof: `grep -c 'AstroImplicitFragment' crates/biome_js_parser/tests/js_test_suite/ok/astro_implicit_fragment.astro_expr.tsx.snap` → **1** (`tag: AstroImplicitFragment { children: JsxChildList [ ...` wrapping BOTH sibling elements).
- Single-element NO-fragment case: fixture `astro_single_element_no_fragment.astro_expr.tsx.snap` AST root is `tag: JsxSelfClosingElement` — no wrapper when only one tag follows (rewind never fires).
- JSX-mode negative control: `grep -c 'expected `<' crates/biome_js_parser/tests/js_test_suite/error/jsx_missing_closing_fragment.jsx.snap` → ≥1 with the new `<p>a</p>\n<div />` lines parsed as ELEMENTS inside the fragment (not AstroImplicitFragment), i.e. the gate did NOT leak into .jsx.
- Spec harness wiring: `grep -c 'astro_expr' crates/biome_js_parser/tests/spec_test.rs` → **1** (`.astro_expr.` filenames get `JsEmbeddingKind::Astro { frontmatter: false, is_class_attribute: false }`).

## Retrieve
```
codebase-memory-mcp cli search_graph --project biome --name-pattern 'parse_astro_implicit_fragment|is_at_astro_adjacent_sibling|is_at_jsx_tag_start'
```
→ `parse_astro_implicit_fragment Function :120-128`, `is_at_astro_adjacent_sibling Function :83-85`, `AstroImplicitFragmentChildren Struct :94-113` (all line-exact at pin).

## Verdict
Adopt: abandon+rewind+reparse is THE reusable pattern for adding dialect-specific productions to shared grammars (Svelte/Vue embeds, template dialects, JSX variants). Adapt the feature-gate plumbing to your source-type enum; omit Biome's specific embedding-kind enum shape.

---
**Erratum (pass-15 drift repair):** supersedes the pass-4 `jsx-tag-skeleton` claim that `parse_jsx_tag_expression` spans :52-70 completing directly after `parse_any_jsx_tag` — at the current pin the function spans :53-79 and contains the checkpoint/abandon/rewind ladder above; `parse_any_jsx_opening_tag` now spans :188-254 with the third arm `is_at_astro_void_element` (:258-263) between slash-self-closing and plain-opening completion.
