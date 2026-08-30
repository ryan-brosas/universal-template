<!-- capsule-v2 -->
# ReparseAssignment event-rewrite visitor — how do you relabel an already-parsed expression subtree as assignment syntax without reparsing?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** When the parsed expression turns out to be a valid assignment target (identifier, member chain, `as`/`satisfies`/`!`, parens), how do you convert its event stream into the `*Assignment` node kinds — and recover when the target is invalid like `a?.b = c` or `++a = b`?

## RewriteParseEvents impl on ReparseAssignment
**Path/Symbol:** `crates/biome_js_parser/src/syntax/assignment.rs:try_expression_to_assignment` (:371-397), `struct ReparseAssignment` (:399-419), `impl RewriteParseEvents for ReparseAssignment` (:426-542).
**Signature:** `fn try_expression_to_assignment(...) -> Result<CompletedMarker, CompletedMarker>` driving `rewrite_events(&mut reparse_assignment, checkpoint, p)`.
**Data Shape:** `parents: Vec<(JsSyntaxKind, Option<RewriteMarker>)>` — index 0 is the re-mapped kind, index 1 `None` means *drop this node from the rewritten tree*; `result: Option<CompletedMarker>`; `inside_assignment: bool` gates which kinds still get remapped.

### Decisive source
```rust
// start_node: only these roots are eligible at all
if !matches!(target.kind(p), JS_PARENTHESIZED_EXPRESSION | JS_STATIC_MEMBER_EXPRESSION
    | JS_COMPUTED_MEMBER_EXPRESSION | JS_IDENTIFIER_EXPRESSION | TS_NON_NULL_ASSERTION_EXPRESSION
    | TS_AS_EXPRESSION | TS_SATISFIES_EXPRESSION | TS_TYPE_ASSERTION_EXPRESSION) { return Err(target); }

JS_REFERENCE_IDENTIFIER => { self.parents.push((kind, None)); return; } // Omit inner identifier
_ => { self.inside_assignment = false;
    if AnyTsType::can_cast(kind) && matches!(self.parents.last(),
        Some((TS_AS_ASSIGNMENT | TS_SATISFIES_ASSIGNMENT | TS_TYPE_ASSERTION_ASSIGNMENT, _))) { kind }
    else { JS_BOGUS_ASSIGNMENT } }

// token(): the optional-chain catch
if matches!(*parent_kind, JS_COMPUTED_MEMBER_ASSIGNMENT | JS_STATIC_MEMBER_ASSIGNMENT)
    && token.kind == T![?.] { *parent_kind = JS_BOGUS_ASSIGNMENT }
```

**Flow:** eligibility check by root kind → replay the recorded events through the visitor: parenthesized→parenthesized-assignment, static/computed member→member-assignment, identifier-expression→identifier-assignment (inner reference identifier *dropped*, not re-emitted), TS wrapper expressions→their assignment twins → any other node inside the assignment flips `inside_assignment=false` and becomes bogus unless it's a TS type under an as/satisfies/assertion parent → `finish_node` re-runs strict-mode `eval`/`arguments` checks per completed `JS_IDENTIFIER_ASSIGNMENT`.
**Invariant:** The visitor is single-pass over events with a marker stack; nodes marked `None` must never be completed, or the tree-sink sees unbalanced markers. Optional chaining (`?.`) can only be detected at token level because the *node* kind doesn't change — hence the token hook demoting the already-started parent. `inside_assignment` is re-enabled in `finish_node` when leaving a TS type child of an assertion parent (:514-524), so `(a as T).b = c` keeps `.b` assignable.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/error/invalid_assignment_target.js` (`++a = b`, `(a +) = b`, `a?.b = b`) plus `error/eval_arguments_assignment.js` (strict-mode eval demotion happens during rewrite).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "ReparseAssignment RewriteParseEvents rewrite_events", limit: 10, fields: ["signature", "name", "file"] });
```
Resolves all five `ReparseAssignment.*` methods (:412-541).

## Verdict
Adopt event-replay rewriting for post-hoc grammar reinterpretation — it preserves tokens/trivia exactly where rewind+reparse would re-lex them; adapt the kind mapping table; omit the TS type-under-assertion special case if the host language has no type-cast expressions. Coverage caveat: full-mode index, metadata_match.
