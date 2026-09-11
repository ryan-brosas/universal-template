<!-- capsule-v2 -->
# Rc-shared Comments + debug-assert discipline — why is the comment store cloned per format call, and what two panics keep rule authors honest?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** how can a format rule iterate `context().comments()` (shared borrow) while writing through the formatter (mutable borrow of context) — and how does CI catch rules that skip suppression checks or drop comments?

## The ownership seam
**Path/Symbol:** `crates/biome_formatter/src/comments.rs` — `Comments { data: Rc<CommentsData<L>> }` (:792-810 with borrow-conflict doc :798-808), suppression API (:930-996), `assert_formatted_all_comments` (:1002-1048), alignable/doc-comment classifiers (:1230-1298); `SourceComment.formatted: Cell<bool>` behind `#[cfg(debug_assertions)]` (:172-173).
**Signature:** `is_suppressed(&self, node) -> bool` / `mark_suppression_checked(&self, node)` / `assert_checked_all_suppressions(&self, root)` — all `&self`, mutation only via interior mutability in debug builds.
**Data Shape:** `CommentsData { root: Option<SyntaxNode>, is_node_suppression: fn(&str)->bool, is_global_suppression: fn(&str)->bool, comments: CommentsMap, with_skipped: FxHashSet, checked_suppressions: RefCell<FxHashSet<SyntaxNode>> }` — the two predicate fn POINTERS are captured from the language's CommentStyle at build time.

### Decisive source
```rust
// comments.rs:794-809 — Rc is not an optimization; it breaks a borrow cycle:
// The use of a [Rc] is necessary to achieve that [Comments] has a lifetime
// that is independent from the [crate::Formatter]. Having independent
// lifetimes is necessary to support the use case where a (formattable object)
// iterates over all comments, and writes them into the [crate::Formatter]
// (mutably borrowing the [crate::Formatter] and in turn its context).
data: Rc<CommentsData<L>>,
```
**Flow:** every accessor (`leading_comments`, etc.) starts with `let comments = f.context().comments().clone();` (trivia.rs :145/:163/:328/:518 do exactly this) so iteration borrows the Rc'd data, not the context. Two debug-only gates then run at end-of-format: (1) `assert_checked_all_suppressions` walks all descendants and PANICS for any non-list/non-root node that never called `is_suppressed` — catching rules that hand-format children without going through `node.format()` (:974-996 panic text names both fixes); (2) `assert_formatted_all_comments` PANICS if any SourceComment's `formatted` Cell stayed false — no comment may be dropped silently. In release both compile to `#[inline(always)]` no-ops. `is_global_suppressed` additionally requires the comment to be a LEADING comment of the file-start node.
**Invariant:** the Rc must wrap ALL mutable state (RefCell included) so clones observe each other's marks — cloning deep would break the formatted-flag protocol. Porters who make `Comments` borrow the context hit E0502 on the very first loop that writes comments while iterating them; porters who gate the asserts out entirely lose biome's strongest rule-authoring guardrail.
**Probe:** `crates/biome_formatter/src/comments.rs` doc example :921-929 pins `is_suppressed` scoping (true for the expression statement, false for the nested call). The two asserts are themselves the executable contract (panic paths); classifier doctests pin `is_alignable_comment`/`is_doc_comment` polarity (:1206-1228, :1261-1282).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "Comments is_suppressed assert_formatted_all_comments", limit: 10, fields: ["signature", "name", "file"] });
// Comments::is_suppressed comments.rs 930-936 (line-exact)
```

## Verdict
Adopt Rc-shared immutable-after-build comment store + debug-assert completion proofs for any formatter with suppression semantics; adapt the fn-pointer style to your trait objects; omit global-suppression logic if your language lacks file-level suppression comments. Coverage caveat: assert-panic paths are exercised by biome's own formatter test suite at scale rather than unit tests here.
