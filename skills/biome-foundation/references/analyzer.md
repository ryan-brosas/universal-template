<!-- capsule-v2 -->
# Rule engine — how do you dispatch lint rules, order diagnostics, handle suppressions, and gate fixes?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome` (full mode, 141,682 nodes / 644,530 edges, generation 2026-08-16). **Question:** a linter's rule engine must run rules cheaply, order diagnostics by source position, honor suppression comments, and keep fix safety/severity consistent. How does `biome_analyze` do it?

## The rule-engine seam
**Path/Symbol:** `crates/biome_analyze/src/` — `lib.rs` (run/phase orchestration), `rule.rs` (1,848L), `query.rs`, `registry.rs`, `signals.rs`, `context.rs`, `services.rs`, `matcher.rs`; representative rules in `crates/biome_js_analyze/src/lint/suspicious/`.
**Signature:** `trait Rule: RuleMeta + Sized { type Query; type State; type Signals: IntoIterator<Item=State>; type Options; fn run(ctx)->Signals; fn diagnostic(ctx,state); fn action(ctx,state) }` (rule.rs:1313-1543). Rules declared via `declare_lint_rule!`.
**Data Shape:** `Query` selects nodes; `State` is the minimal data run produces; `Signals` is an iterator of states; `Options` config. Registration maps `TypeId::of::<SyntaxNode<L>>()` per raw SyntaxKind OR the Input's TypeId to a monomorphized fn-pointer executor (registry.rs:136-254). Phases derive from SERVICES: "What defines a phase is the set of services that a phase offers" (:95-98) — Syntax phase offers nothing (runs immediately), Semantic phase offers the semantic model (runs after full traversal). A rule's phase is chosen by its Query's Services associated type (`phase()` defaults :1322-1324; `()` → Syntax).

### Decisive source
```rust
// rule.rs — the cheap-run/lazy-emit split (verbatim from no_double_equals.rs)
// type State = JsSyntaxToken;  run returns just the operator token (:104-120)
// diagnostic builds a RuleDiagnostic from it (:122-140)
// action builds a BatchMutation rewriting ==/!= to ===/!== (:142-160)
```
```rust
// lib.rs:474-480 — positional suppression matching against an ordered signal queue (verbatim)
// "Search for an active line suppression comment covering the range of this signal: first try
//  to load the last line suppression... otherwise perform a binary search over all the
//  previously seen suppressions to find one with a matching range."
```
**Flow:** Phase 0 parses EVERY comment via a language-provided `SuppressionParser` fn before any syntax rule runs (:289-326) — four variants map from SuppressionKind: Classic→Line, All→TopLevel, RangeStart/RangeEnd (:630-650), with keys for category/rule/rule-instance/plugin (:709-719) and multi-rule comments (`// biome-ignore lint/complexity/useWhile lint/nursery/noUnreachable`). Visitors discover matches out of order; every match pushes a `SignalEntry` into a BinaryHeap whose Ord is REVERSED on start offset (matcher.rs:168-171), so peek/pop yields earliest-first without a global sort. A moving cutoff lets token-driven flushing interleave with traversal (:396-397). The `Break` generic lets LSP consumers stop at first diagnostic while `Never` makes no-break zero-sized (:946-973). Suppression matching happens in `flush_matches` against the position-ordered queue (:398-512). Instance-level suppression exists for per-call-site control (:1363-1374). Two honesty mechanisms: UNUSED suppressions flagged ("Suppression comment has no effect...") and `<explanation>` placeholders rejected (:524-530). Top-level comments after real code denied via token-kind gating (:373-375).
**Services:** RuleContext resolves services at construction via FromServices (:41-44); failure yields `ServicesDiagnostic` "Missing services [SemanticModel] for the rule X" rather than a panic. Demanding `SemanticServices` as your Query's Services SILENTLY PROMOTES the rule to the Semantic phase (semantic.rs:43-49) — the type system is the scheduler. Explicit warning against whole-model queries (:12-16): "Using this type as a Rule Query is discouraged, because it enforces the inspections of an entire document... Prefer Semantic<Node>". The model builds in the SYNTAX phase via a builder visitor whose finish inserts it — skipped when the workspace already inserted one (:150-158). Flavor configuration happens mid-traversal (:106-108).
**Fixes vs suggestions:** `FixKind` is three-valued (:68-86): Safe ("safe to apply. Usually these fixes don't change the semantic of the program"), Unsafe ("unsafe to apply. Usually these fixes remove comments, or change the semantic"). Converts lossily to Applicability (Safe→Always, Unsafe→MaybeIncorrect, None→Err). Config can only NARROW: `fix_kind: none` disables fixes while keeping suppression actions (:557-558). Severity deliberately has NO per-diagnostic setter in Rust rules (:1770-1775): "severity should _not_ be explicitly assigned, since rule categories and configuration define the severity. Currently, this is only used for plugins." RuleSignal force-overwrites severity from METADATA (:521) and appends advisory notes for WIP/nursery rules. `ActionMetadata` defers mutation computation for LSP resolve flows (:79-85); ActionFilter bitflags gate which actions get computed.
**Invariant:** `run` must be CHEAP (signals are queued and may be discarded by suppression before emission — lib.rs:398-512); diagnostic/action materialize lazily only if the signal survives; dispatch is O(1) per node; suppression is a first-class ordered pre-pass matched positionally; severity belongs to the rule (metadata), not the call site; config only narrows fix applicability.
**Probe:** matcher.rs:201-380 builds trees with `//group`, `//group/rule`, `//unknown_group`, `//group/unknown_rule` and asserts exact diagnostic ORDER — "Suppression errors first since we check suppressions before syntax rules" — ending with suppressions/unused; matcher test asserts strictly increasing emitted ranges (47 < 63 < 76 < 97 < 110); no_double_equals' expect_diagnostic fence doubles as a fix test (snapshot must contain the unsafe "Use === instead." action; ignoreNull:false must make `foo == null` diagnose); requesting a semantic-dependent rule in a syntax-only harness must yield exactly the ServicesDiagnostic message; registry.rs:180-184 unreachable! panic text is the contract for misregistering SyntaxNode as a TypeId key.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "Rule run diagnostic action suppression FixKind severity registry", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the cheap-run/lazy-emit Rule split, (TypeId|SyntaxKindSet)→fn-pointer dispatch with service-derived phases, positional suppression pre-pass with unused/unknown reporting, min-heap-by-start-offset emission, service-type-as-scheduler, and FixKind/severity-in-metadata policy; adapt query kinds and suppression comment syntax per language; omit plugin-only severity override and language-specific rules. Coverage caveat: rule behavior is pinned by the matcher tests and expect_diagnostic doc fences; no single integration test isolates the registry.
