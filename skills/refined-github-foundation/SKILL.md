---
name: refined-github-foundation
description: "Use when building browser extensions/userscripts that overlay SPAs: feature lifecycle with per-run abort, CSS-animation element observation, API wrappers with write guards, hotfix kill-switches, and DOM-safe dedup."
disable-model-invocation: true
---
# Refined GitHub: SPA-Overlay Extension Foundation

## Use this for
Build or port a content-script extension that safely patches a soft-navigating SPA (GitHub in particular): register and re-run hundreds of features across navigations with clean teardown, watch for elements without MutationObserver overhead, call the host REST/GraphQL API with repo-scoped sugar and human error taxonomy, guard writes against stale tokens, ship post-release hotfixes without store review, edit structured search queries and hierarchical URLs without corrupting slashed branches, and debug feature flags via interactive bisect. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/feature-loader-lifecycle.md` — import-time registration + globalReady + per-run AbortController registry + soft-nav re-run loop.
- `references/run-conditions.md` — three-bucket declarative predicate algebra (asLongAs/include/exclude) with sync short-circuiting.
- `references/selector-observer.md` — zero-MutationObserver element watching via 1ms keyframe animation + caller-ID seen-marks.
- `references/caller-id-dedupe.md` — stack-line identity → hashed DOM marker classes for idempotent UI insertion.
- `references/history-deduplicator.md` — sentinel-element meta-feature that makes back-navigation restores safe.
- `references/api-rest-wrapper.md` — v3 fetch wrapper: repo-relative paths, metadata-augmented successes, classified error funnel.
- `references/api-graphql-wrapper.md` — v4 wrapper: `repository()` sugar, used-only variable injection, repo-aware cache keys.
- `references/token-identity-gate.md` — one-time token↔user write gate, year-cached login map, synthetic scope fallback for fine-grained PATs.
- `references/error-funnel-reporting.md` — stack-deduped global handlers with reversed-scan feature attribution and pre-filled issue links.
- `references/hotfix-channel.md` — Pages-hosted CSV kill-switches, version-gated rows, cached-merge-at-boot, dev bypass.
- `references/options-rename-migrations.md` — registry-derived defaults, strict-false disable check, rename-carrier migrations.
- `references/toast-progress.md` — long-task toast lifecycle with rAF paint gates and reading-time display formula.
- `references/hotkey-registration.md` — hidden-element `data-hotkey` registration with signal-scoped removal.
- `references/bisect-debugging.md` — log2-reload feature-flag bisection over cross-tab TTL state.
- `references/async-event-loop.md` — queue-buffered async event generator with finally-block listener cleanup.
- `references/async-micro-kit.md` — onetime sentinel, abortable delay, waitFor polling, parallel asyncForEach, ArrayMap.
- `references/click-all-batching.md` — alt-click fan-out with scroll preservation + shift-click range toggling.
- `references/compare-url-parsing.md` — `compare/base...head` grammar: pop/shift/pop assignment for `owner:repo:branch` heads.
- `references/gitref-resolution.md` — synchronous ref ladder (picker → atom feed → pure parse) under partial render.
- `references/github-file-url.md` — five-field URL algebra with prefix-match disambiguation of slashed branches.
- `references/pr-reference-parsing.md` — PR reference regex parsing across titles, commit messages, and URLs.
- `references/search-query-mutator.md` — whitespace-safe search query token addition, removal, and replacement.
- `references/attach-element-insertion.md` — anchor-relative insertion with caller-ID marker dedupe and the sync-callback contract.
- `references/page-fetch-network.md` — memoized page-DOM fetch with selector slicing + background-proxied text fetch for CSP-bound contexts.
- `references/text-linkify-pipeline.md` — guarded linkify-and-shorten pipeline over rendered text + odd/even backtick-span parser.
- `references/safari-companion-bridge.md` — macOS/iOS container-app facade driving extension enabled-state and settings.
- `references/react-controlled-input-writers.md` — native-setter + bubbling-input-event writes into framework-controlled fields.
- `references/whitespace-visualizer.md` — reverse splitText whitespace-run wrapping over syntax-highlighted lines.
- `references/dom-editing-micro-kit.md` — smartBlockWrap, joinJsx, replaceElementTypeInPlace, portal action.
- `references/text-number-formatting-kit.md` — abbreviations, $$-pluralize, looseParseInt DOM numbers, calc() summing, pattern matching.
- `references/link-loss-prevention.md` — bare host URL → markdown link rewriting with index-lookahead idempotence.
- `references/host-widget-controllers.md` — programmatic open→act→close of lazy menus, deferred fragments, button groups, notice banners.
- `references/selector-fixture-registry.md` — paired `<selector>` / `<selector>_` live-URL evidence registry with exact-count assertions.
- `references/comment-author-text-extraction.md` — dual-signal bot-name normalization + rendered-DOM-to-text readback with opt-out marker.
- `references/extension-ops-helpers.md` — calver release-age gating, tab fan-out confirmation, cache-clear feedback, self-removing overlay, signal-scoped classes.
- `references/heat-index-scale.md` — clamped inverse-linear-interpolation heat bucketing onto a fixed color ladder.
- `references/delete-branch-feature-anatomy.md` — destructive-action feature anatomy: four-gate visibility stacking, confirm→toast→DELETE→redirect, encodeURIComponent'd ref paths.
- `references/observe-leaf-resolve-container.md` — surviving CSS-module hash churn: observe the stable leaf node, resolve the mutable ancestor via closestElement inside the callback.
- `references/background-message-router.md` — declarative webext-msg handler map; sender-tab-bound open/close; console-clean hotfix-style proxy; failure-proof welcome latch.
- `references/boot-manifest-esm-bootstrap.md` — 2-line dynamic-import ESM shim + ordered import manifest where order IS registration order.
- `references/react-page-update-signal.md` — per-callback AbortSignal.any(run signal, next 'soft-nav:payload') re-arm adapter for React re-renders.
- `references/field-input-event-guard.md` — composition/autocomplete guard ladder + memoized wrapper listener dedupe + capture-phase field keydown/input adapters.
- `references/pr-merge-detection-ladder.md` — observe-early badge → await confirm click → await badge resolve; ancestor-count and self-injection exclusions.
- `references/singleton-init-lifecycle.md` — useEffect-shaped latest-wins init cleanup + ReusableAbortController signal variant.
- `references/element-removal-promise.md` — memoized ResizeObserver detachment promise that resolves (never rejects) under abort.
- `references/altered-click-delegation.md` — click+auxclick+mousedown triple delegation in capture phase with middle-click autoscroll suppression.

## Capsule map
- **Feature runtime** — `references/feature-loader-lifecycle.md`, `references/run-conditions.md`, `references/history-deduplicator.md`, `references/delete-branch-feature-anatomy.md`: readiness promise, soft-nav re-runs, predicate algebra, back-nav sentinel, destructive-action gating exemplar.
- **DOM watching & injection** — `references/selector-observer.md`, `references/caller-id-dedupe.md`, `references/click-all-batching.md`, `references/attach-element-insertion.md`, `references/dom-editing-micro-kit.md`, `references/whitespace-visualizer.md`, `references/observe-leaf-resolve-container.md`: animation-name callback channel, caller-ID hash marks, alt-click batching, anchor-relative dedupe insertion, composition micro-primitives, splitText whitespace runs, hash-churn adaptation pattern.
- **Host API clients** — `references/api-rest-wrapper.md`, `references/api-graphql-wrapper.md`, `references/token-identity-gate.md`, `references/page-fetch-network.md`: REST sugar, GraphQL query wrapping, token owner verification gate, page-DOM fetch + background-proxied fetch.
- **Operations & hotfixes** — `references/error-funnel-reporting.md`, `references/hotfix-channel.md`, `references/options-rename-migrations.md`, `references/extension-ops-helpers.md`: stack attribution error funnel, CSV hotfix channel, options rename migrations, release-age/tab-fanout/overlay ops kit.
- **UI feedback & debugging** — `references/toast-progress.md`, `references/hotkey-registration.md`, `references/bisect-debugging.md`, `references/host-widget-controllers.md`, `references/heat-index-scale.md`: toast lifecycle, data-hotkey registration, bisect feature flags, lazy-widget automation, heat bucketing.
- **Async & parsing kit** — `references/async-event-loop.md`, `references/async-micro-kit.md`, `references/gitref-resolution.md`, `references/github-file-url.md`, `references/compare-url-parsing.md`, `references/pr-reference-parsing.md`, `references/search-query-mutator.md`: async event generator, async helpers, gitref ladder, URL algebra, compare parser, PR reference parser, search query mutator.
- **Text & identity plane** — `references/text-linkify-pipeline.md`, `references/link-loss-prevention.md`, `references/comment-author-text-extraction.md`, `references/react-controlled-input-writers.md`, `references/text-number-formatting-kit.md`, `references/safari-companion-bridge.md`, `references/selector-fixture-registry.md`: linkify guards, markdown re-linking, bot-author resolution + text readback, controlled-input writes, formatting primitives, Safari container facade, selector evidence registry.
- **Context & event glue** — `references/background-message-router.md`, `references/boot-manifest-esm-bootstrap.md`, `references/react-page-update-signal.md`, `references/field-input-event-guard.md`, `references/pr-merge-detection-ladder.md`, `references/singleton-init-lifecycle.md`, `references/element-removal-promise.md`, `references/altered-click-delegation.md`: background protocol + boot ordering, host-event adapters (React updates, field input, merge detection), and imperative-init lifecycle primitives.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf. Pass 3 (drift re-entry @3187161) added the destructive-action feature anatomy (#9974) and the observe-leaf/resolve-container adaptation (#9957) as the two diff-driven seams; both are reusable harness patterns, not product surface. Pass 4 (@3187161, deep pass) mined the uncited cross-context & event glue plane whole: background router, boot manifest, and the github-events/helpers lifecycle primitives (8 capsules). Remaining unmined mass (recorded): context-glue stragglers (`helpers/preserve-scroll.ts`, `used-storage.ts`, `safe-create-tab.ts`+`open-options.tsx`, `history.ts`), `.ts` components (`components/extensible-nav-store.ts` + direct test, `components/tooltip.tsx`), build plane (`build/readme-parser.ts` + rollup manifest wiring), `github-helpers/index.ts` residual route-context helpers, individual feature implementations ×~190 JS + 17 CSS-only (product surface — mine exemplars only if a NEW cross-feature pattern emerges), Svelte options UI internals, `test/web-ext-profile` fixtures.

## Provenance
refined-github (MIT), `main@3187161079033cc1eda1731044ba8a2fdd7b69b4` (pass 4 deep pass; pass 3 was drift re-entry @`3187161`; passes 1–2 pinned `3bbe6088fe301d0d5cf1ae751a49307005762a68`, fast-forwarded +4 commits); Codebase Memory project `refined-github` (full mode, ready, re-indexed 2026-08-24 at HEAD = base_sha `3187161…`; parse_partial files are Swift/Svelte/CSS style sheets only — no cited TS range falls inside a flagged range). Work record: `/mnt/hdd/utopia/inspo/refined-github-work/{state,research,verification}.md`.

## Full view (memory graph)
Revalidate `refined-github` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. At pass-3 re-verification: 2,724 nodes / 7,990 edges at `3187161`; stdin coverage check green on all newly cited paths (no_recorded_issue); live search_graph resolves `deleteBranch` (:15–23) and `cleanPrHeader` (:93–122) line-exact; adversarial cross-project query against `qodana-action` returns total:0. Crown primitives unchanged from pass 2 (`feature-manager.add` fan-in 183, `selector-observer.observe` fan-in 141). Pass-4 re-verification (2026-08-26): same pin/counts re-confirmed live (ready, head==base==3187161); coverage `no_recorded_issue` ×15 on all pass-4 cited paths @ gen 2026-08-24T14:04:43Z; inbound traces resolve all 8 new seams to named feature consumers; unit tests exist only for pure helpers — the entire context/event-glue plane is browser-bound, so its capsules carry executed deterministic source pins instead of fabricated test claims (`vitest --run` unrunnable: no node_modules at checkout).

## Boundaries
Adopt the feature lifecycle, observer/dedupe primitives, API wrapper contracts, hotfix channel, query/URL algebras, linkify/author/text round-trip plane, and widget-controller sequences — they are host-agnostic harness mechanics. Adapt all selectors, GitHub-specific page detection (`github-url-detection`), error copy, DOM class conventions, calver version parsing, and heat-ladder polarity to your target site. Omit the 300 feature implementations themselves (product surface), the Svelte options UI internals and the Safari app shell beyond the bridge facade (host-specific), and the deprecated `deduplicate` loader option (superseded by caller-ID marks).
