<!-- capsule-v2 -->
# Lazy signals & action filters — why is diagnostic() re-entrant and how do fixes get disabled without losing suppressions?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** a queued signal may be suppressed before emission — what must stay lazy, and how does `fix: none` keep suppression quickfixes alive while killing rule fixes?

## The signal seam
**Path/Symbol:** `crates/biome_analyze/src/signals.rs` — `AnalyzerSignal` trait (:87-94), `DiagnosticSignal` (:100-176), `PluginSignal` (:186-250), `AnalyzerAction` (:258-280), `ActionFilter`/`ActionKind` (:24-74), `RuleSignal` (:472-725), `ActionMetadata` (:78-83).
**Signature:** `trait AnalyzerSignal<L> { fn diagnostic(&self) -> Option<AnalyzerDiagnostic>; fn actions(&self, filter: ActionFilter) -> AnalyzerActionIter<L>; fn actions_metadata(&self) -> Vec<ActionMetadata>; fn transformations(&self) -> AnalyzerTransformationIter<L> }`.
**Data Shape:** `AnalyzerAction { rule_name: Option<(group, rule)>, category: ActionCategory, applicability: Applicability, message: MarkupBuf, mutation: BatchMutation<L>, text_edit: Option<(TextRange, TextEdit)> }` — plugin rewrites carry a pre-computed text_edit that TAKES PRECEDENCE over the (empty) mutation (:264, :294-306).

### Decisive source
```rust
// signals.rs:553-571 — config can only NARROW; fix "none" keeps suppression actions:
let fix_disabled = matches!(self.options.rule_fix_kind::<R>(), Some(FixKind::None));
let configured_applicability = if filter.is_rule_fix() && !fix_disabled {
    if let Some(fix_kind) = self.options.rule_fix_kind::<R>() {
        match fix_kind {
            FixKind::None => None,
            FixKind::Safe => Some(Applicability::Always),
            FixKind::Unsafe => Some(Applicability::MaybeIncorrect),
        }
    } else { None }
} else { None };
```
```rust
// signals.rs:512-533 + 535-550 — EVERY call rebuilds a RuleContext from options
// (globals/quote/jsx/options unwrap_or_default) then runs R::diagnostic;
// severity force-overwritten from METADATA; WIP/nursery notes appended at emit time.
diagnostic.severity = ctx.metadata().severity;
```
**Flow:** rules run once in `RegistryRule::run` producing `R::Signals`; each becomes a boxed `RuleSignal` in the heap. Only when flushed AND unsuppressed does the consumer call `diagnostic()`/`actions(filter)` — so `run` must be cheap, and diagnostic/action closures must be RE-ENTRANT (RuleSignal::diagnostic builds a fresh RuleContext every call because &self). `actions` computes three independent ladders gated by ActionFilter bits: rule fix (skipped when `FixKind::None` configured or metadata None; applicability = config override else action's own), inline suppression (`R::text_range` → `R::inline_suppression`, always Applicability::Always), top-level suppression. `actions_metadata` NEVER computes mutations (LSP resolve flow) and reports suppression metadata for Lint|Action|Syntax categories even when fixes are disabled (:646-692). PluginSignal preserves `DiagnosticKind::Rule` (not Raw) so embedded-language offset adjustment applies (its doc comment :178-185).
**Invariant:** nothing expensive happens before emission (suppressed signals never build diagnostics); severity belongs to metadata, not the rule author; `text_edit.or_else(|| mutation.to_text_range_and_edit())` ordering is the plugin/CST bridge; transformations are a separate channel from actions.
**Probe:** upstream rule test fences (`expect_diagnostic`) double as action snapshots (no_double_equals' unsafe "Use === instead." must appear); matcher.rs order tests exercise DiagnosticSignal emission end-to-end; no dedicated unit test for ActionFilter bit combos — the ladder branches above are the pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "RuleSignal AnalyzerSignal DiagnosticSignal ActionFilter", limit: 10, fields: ["signature", "name", "file"] });
// AnalyzerSignal signals.rs 87-94; PluginSignal 186-250; RuleSignal 472-725 (line-exact)
```

## Verdict
Adopt the lazy re-entrant signal trio (diagnostic/actions/metadata), the ActionFilter bit-gated triple ladder, config-narrows-applicability policy, and metadata-owned severity with emit-time advisory notes; adapt the action-category vocabulary; omit PluginSignal's embedded-offset channel unless porting plugins over foreign embeds.
