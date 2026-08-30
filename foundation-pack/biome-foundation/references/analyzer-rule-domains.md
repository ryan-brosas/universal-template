<!-- capsule-v2 -->
# Rule domains & suppression kinds — how does `RuleDomain` gate a rule before it ever runs, and which ignore-variants exist?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** some rules must not fire inside test files or specific project domains — how is that expressed statically, and what suppression comment shapes map to what runtime behavior?

## The domain/suppression-kind seam
**Path/Symbol:** `crates/biome_analyze/src/rule.rs` — `RuleDomain` (:~1200s, enum with Test/Json etc.), `RuleMetadata` fields incl. `domains: &[RuleDomain]`, `RuleSource`/`RuleSourceKind` (ESLint/oxlint provenance), `instances_for_signal`; `lib.rs` — `AnalyzerSuppressionKind` (:709-718) and `to_analyzer_suppressions` category ladder (:721-780); `matcher.rs` — `SignalEntry.instances` (:154-165).
**Signature:** `enum AnalyzerSuppressionKind { Everything(RuleCategory), Rule(&'a str), RuleInstance(&'a str, &'a str), Plugin(Option<&'a str>) }`; mapping `Classic→Line, All→TopLevel, RangeStart→RangeStart, RangeEnd→RangeEnd` (:640-649).
**Data Shape:** `to_analyzer_suppressions(suppression: Suppression, piece_range: TextRange) -> Vec<AnalyzerSuppression>` — one comment yields MULTIPLE suppressions (one per category entry); every range rebased by `piece_range.add_start(...)`; syntax-category bypasses are deliberately never skipped ("Don't allow skipping of syntax since we want explicit bypasses as an escape hatch only", :739-740).

### Decisive source
```rust
// lib.rs:752-775 — the strip-prefix ladder assigns the RULE CATEGORY from the
// comment prefix, with instance values only for lint:
} else {
    let category = key.name();
    if let Some(rule) = category.strip_prefix("lint/") { ... }        // + optional (instance)
    else if let Some(action) = category.strip_prefix("assist/") { .. } // "action instances aren't supported yet"
    else if let Some(rule) = category.strip_prefix("syntax/") { .. }
}
```
**Flow:** a rule declares domains in its metadata; the CLI/registry consults them during filtering so domain-disabled rules are never registered for a file (cheap static gate BEFORE any traversal cost). At signal time `R::suppressed_nodes(&ctx, &result, &mut state.suppressions)` lets a rule mark nodes whose subtree should skip future matching (registry executor short-circuit). Instance-level comments (`useExhaustiveDependencies(foo)`) ride `SignalEntry.instances: Box<[Box<str>]>`; flush_matches removes matched instances lazily and only treats the signal suppressed when EVERY instance is covered (lib.rs:448-495). RuleSource metadata documents ESLint/oxlint origins (`RuleSourceKind::SameLogic` vs inspired) — documentation-only but shipped through the docs pipeline.
**Invariant:** categories come from the comment PREFIX not the payload; lint keeps per-instance granularity while assist actions do not; `Everything(category)` (bare `lint`) suppresses the whole category for that line/top-level/range; domain gating happens at registration time, making it invisible to flush-time logic.
**Probe:** matcher.rs tests cover unknown-rule/unknown-group diagnostics and multi-rule comments (`// biome-ignore lint/a lint/b`); biome_suppression unit tests pin `(category, subcategory, value)` triples incl. plugin names; upstream `noUndeclaredVariables` domain fixtures pin Test-domain behavior.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "RuleDomain AnalyzerSuppressionKind instances_for_signal", limit: 10, fields: ["signature", "name", "file"] });
// to_analyzer_suppressions lib.rs 721-780; AnalyzerSuppressionKind 709-718 (line-exact)
```

## Verdict
Adopt prefix-derived categories, registration-time domain gating, instance-carrying signals with all-instances-must-match semantics, and explicit-bypass-only syntax suppressions; adapt domain vocabulary to your host; omit RuleSource provenance unless porting docs tooling.
