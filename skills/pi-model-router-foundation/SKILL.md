---
name: pi-model-router-foundation
description: Use when porting per-turn LLM tier-routing machinery — heuristic routing ladders with sticky phase bias, custom-rule highest-tier precedence, fall-up tier resolution, fail-open LLM classifiers with a two-line wire protocol, Google thought-signature continuation pins, image-capability tier escalation, fallback chains gated by a content-received latch, plus the router config plane — layered global/project merge, canonical provider/model ref grammar, alias-then-canonical resolution, warn-and-degrade normalization, registry-over-config capacity precedence with honest truncation, and per-tier thinking-level derivation with downward clamping — capsule-v2 source maps with decisive excerpts and graph retrieval.
---
# pi-model-router: per-turn tier-routing foundation

## Use this for
Use when porting model routers, cost/quality tier selectors, or provider-delegation
shims for coding agents — anywhere a host request must be re-targeted per turn to a
high/medium/low model tier with explainable reasoning. Source code and direct tests
are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/routing-heuristic-ladder.md` — how do I classify a turn into high/medium/low deterministically before any LLM call?
- `references/custom-rule-tier-precedence.md` — how do user-supplied rules override heuristics and the classifier?
- `references/tier-resolution-fall-ladder.md` — what happens when the chosen tier is not configured in the profile?
- `references/classifier-two-line-fail-open.md` — how does the optional LLM classifier override stay cheap and never break routing?
- `references/google-thought-signature-continuation-pin.md` — why must a mid-task tool-result continuation keep the same Google model?
- `references/image-tier-escalation-fallback-filter.md` — how are image attachments forced onto a capable tier without losing the decision trail?
- `references/fallback-chain-content-latch.md` — when may the chain try the next model, and when must an error reach the caller?
- `references/config-layered-load-merge.md` — how do global and project router config files layer and merge without a broken file killing the extension?
- `references/canonical-model-ref-grammar.md` — where does the `provider/model` grammar live so validation and runtime lookups agree?
- `references/alias-resolution-two-stage.md` — how do model aliases expand to canonical refs in tiers, fallbacks, and classifier config?
- `references/warn-and-degrade-normalization.md` — how is partially-invalid config normalized without throwing away valid portions?
- `references/capacity-precedence-honesty.md` — what context window should a virtual router model advertise vs enforce?
- `references/thinking-levels-derivation-clamp.md` — how are per-tier thinking levels derived once and clamped at stream time?

## Capsule map
- **Heuristic ladder** — `routing-heuristic-ladder`: ordered keyword/shape ladder with phase-sticky word-count thresholds; order is the contract.
- **Custom rules** — `custom-rule-tier-precedence`: case-insensitive match set, highest-tier-wins, `isRuleMatched` suppresses the classifier.
- **Tier resolution** — `tier-resolution-fall-ladder`: resolve unavailable tiers up first (low→medium→high), down second; throw only if the final tier has no config.
- **Classifier** — `classifier-two-line-fail-open`: `Tier:`/`Reasoning:` two-line protocol parsed from streamed deltas; any failure returns undefined and heuristics stand.
- **Google continuation pin** — `google-thought-signature-continuation-pin`: preserve the previous google/thinking decision across tool-result continuations to avoid thought-signature replay errors.
- **Image escalation** — `image-tier-escalation-fallback-filter`: escalate tiers until one declares image input, then filter the executed chain by capability with a degenerate last resort.
- **Fallback chain** — `fallback-chain-content-latch`: pre-content errors advance the chain; post-content errors propagate; honesty truncation and thinking clamp per attempt.
- **Layered load/merge** — `config-layered-load-merge`: fail-open file parse, global←project layering, per-tier spread merge; scalar lists replace rather than concatenate.
- **Model-ref grammar** — `canonical-model-ref-grammar`: first-slash split with trim-and-throw; validate-and-discard at config time, destructure at runtime.
- **Alias resolution** — `alias-resolution-two-stage`: exact-key alias→canonical + definition carry-through; re-validate canonically; degrade at entry < tier < profile scope.
- **Warn-and-degrade normalization** — `warn-and-degrade-normalization`: one accumulated warnings array; clamp scalars, disable dead tiers, skip empty profiles, never throw.
- **Capacity precedence** — `capacity-precedence-honesty`: registry > tier > alias > default; report max-across-tiers, truncate to the routed tier's actual limit.
- **Thinking levels** — `thinking-levels-derivation-clamp`: derive resolvedThinkingLevels once (explicit arrays authoritative), clamp downward along the level ordinal at stream time.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
pi-model-router (MIT), `main@002b48f9bb03c068e0ef97eb230f49df57a24f93`; Codebase Memory project `pi-model-router` (ready FULL, 253 nodes / 1082 edges, generation 2026-08-25T19:59:04Z, zero parse-partial / skipped files; `.git` excluded by design).

## Full view (memory graph)
Revalidate `pi-model-router` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt the pure decision kernel (`routing.ts` + `RoutingDecision`) and the fail-open classifier posture verbatim; adapt the Pi-specific provider registration, session-state plumbing (`index.ts`), and registry/auth lookups to your host; omit the slash-command/UI planes and the example config unless you port the whole extension. The config plane (`config.ts`) is the second fully-mined subsystem: its warn-and-degrade normalization, layered merge, and resolution helpers are adopt-verbatim contracts.
