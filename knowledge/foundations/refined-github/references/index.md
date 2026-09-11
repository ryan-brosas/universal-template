<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->

# Refined GitHub: SPA-Overlay Extension Foundation

## Use this for
Build or port a content-script extension that safely patches a soft-navigating SPA (GitHub in particular): register and re-run hundreds of features across navigations with clean teardown, watch for elements without MutationObserver overhead, call the host REST/GraphQL API with repo-scoped sugar and human error taxonomy, guard writes against stale tokens, ship post-release hotfixes without store review, edit structured search queries and hierarchical URLs without corrupting slashed branches, and debug feature flags via interactive bisect. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./feature-loader-lifecycle.md` — import-time registration + globalReady + per-run AbortController registry + soft-nav re-run loop.
- `./run-conditions.md` — three-bucket declarative predicate algebra (asLongAs/include/exclude) with sync short-circuiting.
- `./selector-observer.md` — zero-MutationObserver element watching via 1ms keyframe animation + caller-ID seen-marks.
- `./caller-id-dedupe.md` — stack-line identity → hashed DOM marker classes for idempotent UI insertion.
- `./history-deduplicator.md` — sentinel-element meta-feature that makes back-navigation restores safe.
- `./api-rest-wrapper.md` — v3 fetch wrapper: repo-relative paths, metadata-augmented successes, classified error funnel.
- `./api-graphql-wrapper.md` — v4 wrapper: `repository()` sugar, used-only variable injection, repo-aware cache keys.
- `./token-identity-gate.md` — one-time token↔user write gate, year-cached login map, synthetic scope fallback for fine-grained PATs.
- `./error-funnel-reporting.md` — stack-deduped global handlers with reversed-scan feature attribution and pre-filled issue links.
- `./hotfix-channel.md` — Pages-hosted CSV kill-switches, version-gated rows, cached-merge-at-boot, dev bypass.
- `./options-rename-migrations.md` — registry-derived defaults, strict-false disable check, rename-carrier migrations.
- `./toast-progress.md` — long-task toast lifecycle with rAF paint gates and reading-time display formula.
- `./hotkey-registration.md` — hidden-element `data-hotkey` registration with signal-scoped removal.
- `./bisect-debugging.md` — log2-reload feature-flag bisection over cross-tab TTL state.
- `./async-event-loop.md` — queue-buffered async event generator with finally-block listener cleanup.
- `./async-micro-kit.md` — onetime sentinel, abortable delay, waitFor polling, parallel asyncForEach, ArrayMap.
- `./click-all-batching.md` — alt-click fan-out with scroll preservation + shift-click range toggling.
- `./compare-url-parsing.md` — `compare/base...head` grammar: pop/shift/pop assignment for `owner:repo:branch` heads.
- `./gitref-resolution.md` — synchronous ref ladder (picker → atom feed → pure parse) under partial render.
- `./github-file-url.md` — five-field URL algebra with prefix-match disambiguation of slashed branches.
- `./pr-reference-parsing.md` — PR reference regex parsing across titles, commit messages, and URLs.
- `./search-query-mutator.md` — whitespace-safe search query token addition, removal, and replacement.
- `./attach-element-insertion.md` — anchor-relative insertion with caller-ID marker dedupe and the sync-callback contract.
- `./page-fetch-network.md` — memoized page-DOM fetch with selector slicing + background-proxied text fetch for CSP-bound contexts.
- `./text-linkify-pipeline.md` — guarded linkify-and-shorten pipeline over rendered text + odd/even backtick-span parser.
- `./safari-companion-bridge.md` — macOS/iOS container-app facade driving extension enabled-state and settings.
- `./react-controlled-input-writers.md` — native-setter + bubbling-input-event writes into framework-controlled fields.
- `./whitespace-visualizer.md` — reverse splitText whitespace-run wrapping over syntax-highlighted lines.
- `./dom-editing-micro-kit.md` — smartBlockWrap, joinJsx, replaceElementTypeInPlace, portal action.
- `./text-number-formatting-kit.md` — abbreviations, $$-pluralize, looseParseInt DOM numbers, calc() summing, pattern matching.
- `./link-loss-prevention.md` — bare host URL → markdown link rewriting with index-lookahead idempotence.
- `./host-widget-controllers.md` — programmatic open→act→close of lazy menus, deferred fragments, button groups, notice banners.
- `./selector-fixture-registry.md` — paired `<selector>` / `<selector>_` live-URL evidence registry with exact-count assertions.
- `./comment-author-text-extraction.md` — dual-signal bot-name normalization + rendered-DOM-to-text readback with opt-out marker.
- `./extension-ops-helpers.md` — calver release-age gating, tab fan-out confirmation, cache-clear feedback, self-removing overlay, signal-scoped classes.
- `./heat-index-scale.md` — clamped inverse-linear-interpolation heat bucketing onto a fixed color ladder.
- `./delete-branch-feature-anatomy.md` — destructive-action feature anatomy: four-gate visibility stacking, confirm→toast→DELETE→redirect, encodeURIComponent'd ref paths.
- `./observe-leaf-resolve-container.md` — surviving CSS-module hash churn: observe the stable leaf node, resolve the mutable ancestor via closestElement inside the callback.
- `./background-message-router.md` — declarative webext-msg handler map; sender-tab-bound open/close; console-clean hotfix-style proxy; failure-proof welcome latch.
- `./boot-manifest-esm-bootstrap.md` — 2-line dynamic-import ESM shim + ordered import manifest where order IS registration order.
- `./react-page-update-signal.md` — per-callback AbortSignal.any(run signal, next 'soft-nav:payload') re-arm adapter for React re-renders.
- `./field-input-event-guard.md` — composition/autocomplete guard ladder + memoized wrapper listener dedupe + capture-phase field keydown/input adapters.
- `./pr-merge-detection-ladder.md` — observe-early badge → await confirm click → await badge resolve; ancestor-count and self-injection exclusions.
- `./singleton-init-lifecycle.md` — useEffect-shaped latest-wins init cleanup + ReusableAbortController signal variant.
- `./element-removal-promise.md` — memoized ResizeObserver detachment promise that resolves (never rejects) under abort.
- `./altered-click-delegation.md` — click+auxclick+mousedown triple delegation in capture phase with middle-click autoscroll suppression.
- `./extensible-nav-store-tab-store.md` — multi-contributor tab registry: three writable stores merged by one derived (before-anchor splices, stable demotion partition, sequential first-match selection).
- `./tooltip-component.md` — id-linked native `<tool-tip>` popovers portaled into the SPA-surviving container; imperative + ref-callback attach pair; lint-enforced hotkey-tooltip contract.
- `./preserve-scroll-anchor.md` — capture anchor top now / rAF-deferred scrollBy delta restore around self-inflicted layout shifts.
- `./safe-tab-options-open.md` — single `chrome.tabs.create` choke point with mobile-Firefox openerTabId strip, restricted-syntax lint enforcement, background-routed options-page open.
- `./readme-feature-metadata-parser.md` — README-as-build-contract: regex feature-metadata extraction, file-snapshot pins, per-file doc↔manifest↔source invariant engine.
- `./route-context-url-algebra.md` — limit-split pathname conversation number, slash-validating repo URL builder, last-'@' tag parsing, three-ladder version-tag selection, asymmetric username normalization, host-socket poke.
- `./commit-message-trailer-normalization.md` — squash-commit message mechanics: canonical-cased trailer Set preservation with privacy-email exclusion, conditional closing-keyword retention, closed-type conventional parsing, trailing-#N strip and its inverse machine.
- `./storage-byte-accounting-polyfill.md` — native-first getBytesInUse ladder with TextEncoder byte-count fallback for exists-but-throws engines; quota display with low-space warning invariant.
- `./url-hash-replacestate-cleanup.md` — URL hash as ephemeral state / one-shot deep-link trigger, cleaned via replaceState preserving history.state without a history entry.
- `./css-is-not-selector-builder.md` — 13-line `:is()`/`:not()` selector-list builders with array-or-variadic overloads as the cross-layer selector vocabulary.
- `./conversation-lock-resolution-ladder.md` — concurrent multi-source host-fact resolution: first-DEFINED-wins over React preloaded data / moderator-only DOM / token-gated API; fail-closed by non-resolution.
- `./repo-permission-capability-cache.md` — one cached permission enum with fail-closed ladders + an asymmetric DOM fast-path that deliberately cannot be cached.
- `./dom-first-ttl-value-cache.md` — DOM-first/API-fallback repo-scoped value cache (maxAge + staleWhileRevalidate), authoritative-page scoping, no-optional-args updater rule, prefix-terminated branch comparison.
- `./spa-navigation-url-store.md` — module-scoped readable URL store: refresh-on-subscribe staleness fix, hash-only strip, per-subscriber host-navigate listener.

## Capsule map
- **Feature runtime** — `./feature-loader-lifecycle.md`, `./run-conditions.md`, `./history-deduplicator.md`, `./delete-branch-feature-anatomy.md`: readiness promise, soft-nav re-runs, predicate algebra, back-nav sentinel, destructive-action gating exemplar.
- **DOM watching & injection** — `./selector-observer.md`, `./caller-id-dedupe.md`, `./click-all-batching.md`, `./attach-element-insertion.md`, `./dom-editing-micro-kit.md`, `./whitespace-visualizer.md`, `./observe-leaf-resolve-container.md`, `./preserve-scroll-anchor.md`, `./css-is-not-selector-builder.md`: animation-name callback channel, caller-ID hash marks, alt-click batching, anchor-relative dedupe insertion, composition micro-primitives, splitText whitespace runs, hash-churn adaptation pattern, scroll-stability capture/restore pair, :is()/:not() selector-list builders.
- **Host API clients** — `./api-rest-wrapper.md`, `./api-graphql-wrapper.md`, `./token-identity-gate.md`, `./page-fetch-network.md`, `./repo-permission-capability-cache.md`, `./dom-first-ttl-value-cache.md`: REST sugar, GraphQL query wrapping, token owner verification gate, page-DOM fetch + background-proxied fetch, cached permission enum with uncacheable asymmetric DOM fast-path, DOM-first TTL value cache.
- **Operations & hotfixes** — `./error-funnel-reporting.md`, `./hotfix-channel.md`, `./options-rename-migrations.md`, `./extension-ops-helpers.md`, `./safe-tab-options-open.md`, `./storage-byte-accounting-polyfill.md`: stack attribution error funnel, CSV hotfix channel, options rename migrations, release-age/tab-fanout/overlay ops kit, lint-enforced tab-creation choke point + background-routed options open, native-first storage byte accounting with serialization fallback.
- **UI feedback & debugging** — `./toast-progress.md`, `./hotkey-registration.md`, `./bisect-debugging.md`, `./host-widget-controllers.md`, `./heat-index-scale.md`: toast lifecycle, data-hotkey registration, bisect feature flags, lazy-widget automation, heat bucketing.
- **Async & parsing kit** — `./async-event-loop.md`, `./async-micro-kit.md`, `./gitref-resolution.md`, `./github-file-url.md`, `./compare-url-parsing.md`, `./pr-reference-parsing.md`, `./search-query-mutator.md`, `./route-context-url-algebra.md`, `./conversation-lock-resolution-ladder.md`: async event generator, async helpers, gitref ladder, URL algebra, compare parser, PR reference parser, search query mutator, route-context URL/tag algebra from the SPA URL bar, first-defined-wins multi-source fact resolution.
- **Text & identity plane** — `./text-linkify-pipeline.md`, `./link-loss-prevention.md`, `./comment-author-text-extraction.md`, `./react-controlled-input-writers.md`, `./text-number-formatting-kit.md`, `./safari-companion-bridge.md`, `./selector-fixture-registry.md`, `./commit-message-trailer-normalization.md`: linkify guards, markdown re-linking, bot-author resolution + text readback, controlled-input writes, formatting primitives, Safari container facade, selector evidence registry, squash-commit trailer preservation + conventional parsing.
- **Context & event glue** — `./background-message-router.md`, `./boot-manifest-esm-bootstrap.md`, `./react-page-update-signal.md`, `./field-input-event-guard.md`, `./pr-merge-detection-ladder.md`, `./singleton-init-lifecycle.md`, `./element-removal-promise.md`, `./altered-click-delegation.md`, `./url-hash-replacestate-cleanup.md`: background protocol + boot ordering, host-event adapters (React updates, field input, merge detection), imperative-init lifecycle primitives, ephemeral URL-hash state with replaceState cleanup.
- **UI components & stores** — `./extensible-nav-store-tab-store.md`, `./tooltip-component.md`, `./spa-navigation-url-store.md`: multi-contributor tab registry with three-store merge, id-linked portaled tooltips over re-rendering hosts, live soft-nav URL store with refresh-on-subscribe.
- **Build & catalog contracts** — `./readme-feature-metadata-parser.md`: README-as-build-contract metadata extraction with snapshot pins and per-file invariant engine.

## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf. Pass 3 (drift re-entry @3187161) added the destructive-action feature anatomy (#9974) and the observe-leaf/resolve-container adaptation (#9957) as the two diff-driven seams; both are reusable harness patterns, not product surface. Pass 4 (@3187161, deep pass) mined the uncited cross-context & event glue plane whole: background router, boot manifest, and the github-events/helpers lifecycle primitives (8 capsules). Pass 5 (@3187161, deep pass) mined the UI-store/components plane + context-glue stragglers + build metadata plane: extensible-nav-store (with its direct test), tooltip component pair, preserve-scroll, safe-create-tab+open-options (lint-enforced choke point), and the readme-parser build contract (5 capsules). Pass 6 (@3187161, deep pass) mined the route-context residual + commit-message normalization trio (all three with direct tests) + options-plane stragglers + selector-string builder: route-context URL/tag algebra (with index.test.ts), squash-commit trailer preservation/conventional parsing/trailing-#N strip, storage byte-accounting polyfill, ephemeral URL-hash replaceState cleanup, and the :is()/:not() builders (5 capsules). Pass 7 (@3187161, closure-audit deep pass) re-audited the entire uncited mass (48 non-feature files) and mined the four real seams it surfaced: first-defined-wins multi-source fact resolution (is-conversation-locked), cached permission enum with uncacheable asymmetric DOM fast-path (get-user-permission), DOM-first TTL value cache (get-default-branch + is-default-branch), and the soft-nav URL store (components/url.ts) — 4 capsules. CLOSURE: every remaining uncited file has a recorded reason in the work record — small single-purpose wrappers (bugs-label, get-pr-info, get-user-avatar, netiquette, icon-loading — one API call or static JSX each; the wrapper CONTRACT is already capsuled), rgh-links.tsx (+test — links to the RGH repo itself), conversation-activity-filter.ts (11 L state store), is-low-quality-comment.ts (+test — product word-list heuristic), options/{identify-feature,toggle-all,reload-without}.ts + options.tsx + graphql.svelte + dom-chef.svelte + Svelte UI ×25 (host-specific options/welcome UI), globals.d.ts/types.d.ts (type declarations), set-status-filter.test.ts (test of an already-cited source), eslint-rules/* (lint tooling), build/new-feature.sh (scaffolding), features/* ×~190 JS + 17 CSS-only (product surface), `test/web-ext-profile` fixtures → status `complete`; reopen with diff-first re-adjudication on any HEAD advance past `3187161`.

## Provenance
refined-github (MIT), `main@3187161079033cc1eda1731044ba8a2fdd7b69b4` (pass 7 closure-audit deep pass; pass 6 deep pass; pass 5 deep pass; pass 4 deep pass; pass 3 was drift re-entry @`3187161`; passes 1–2 pinned `3bbe6088fe301d0d5cf1ae751a49307005762a68`, fast-forwarded +4 commits); Codebase Memory project `refined-github` (full mode, ready, re-indexed 2026-08-24 at HEAD = base_sha `3187161…`; parse_partial files are Swift/Svelte/CSS style sheets only — no cited TS range falls inside a flagged range). Work record: `$REFERENCE_ROOT/.skill-mining-work/refined-github/{state,research,verification}.md`.

## Full view (memory graph)
Revalidate `refined-github` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. At pass-3 re-verification: 2,724 nodes / 7,990 edges at `3187161`; stdin coverage check green on all newly cited paths (no_recorded_issue); live search_graph resolves `deleteBranch` (:15–23) and `cleanPrHeader` (:93–122) line-exact; adversarial cross-project query against `qodana-action` returns total:0. Crown primitives unchanged from pass 2 (`feature-manager.add` fan-in 183, `selector-observer.observe` fan-in 141). Pass-4 re-verification (2026-08-26): same pin/counts re-confirmed live (ready, head==base==3187161); coverage `no_recorded_issue` ×15 on all pass-4 cited paths @ gen 2026-08-24T14:04:43Z; inbound traces resolve all 8 new seams to named feature consumers; unit tests exist only for pure helpers — the entire context/event-glue plane is browser-bound, so its capsules carry executed deterministic source pins instead of fabricated test claims (`vitest --run` unrunnable: no node_modules at checkout). Pass-5 re-verification (2026-08-27): pin/counts re-confirmed live via vendor CLI (ready, head==base==3187161, 2,724n/7,990e); coverage `no_recorded_issue` ×15 on all pass-5 cited paths @ gen 2026-08-24T14:04:43Z; inbound traces: withTooltipRef callers_total 22, safeCreateTab callers_total 4 (all background.ts), preserveScroll callers_total 2; direct tests read in full for extensible-nav-store (11 cases) and readme-parser/features (snapshot + invariant engine) but NOT executed (standing runner block). Pass-6 re-verification (2026-08-28): pin/counts re-confirmed live via vendor CLI (ready, head==base==3187161, 2,724n/7,990e); coverage `no_recorded_issue` ×17 on all pass-6 cited paths @ gen 2026-08-24T14:04:43Z; inbound traces: getConversationNumber callers_total 24, buildRepoUrl 45, cleanCommitMessage/parseConventionalCommit/cleanPrCommitTitle each 1 (one dedicated consumer per helper), css-selectors.is 17 (== import-site grep count); direct tests read in full for the commit-message trio (48 assertions) and index.test.ts (33 assertions across 4 functions) but NOT executed (standing runner block); two graph-quality data points recorded — `isPermalink` has no graph node (mem-wrapped const arrow, source-read citation) and `removeHashFromUrlBar` inbound trace over-matched (145 vs actual 2 consumers). Pass-7 re-verification (2026-08-29): pin/counts re-confirmed live via vendor CLI (ready, head==base==3187161, 2,724n/7,990e); coverage `no_recorded_issue` ×14 on all pass-7 cited paths @ gen 2026-08-24T14:04:43Z; inbound traces: isConversationLocked 1 (locked-issue), getDefaultBranch 14, userIsModerator 2 — with two under-count anomalies vs direct grep (userIsAdmin 0-graph/1-grep, isDefaultBranch 0-graph/3-grep: svelte/default-import edges missing; source wins); get_code_snippet byte-comparison green on isConversationLocked/getViewerPermission/userIsModerator/getDefaultBranch/stripHash; closure audit closed all 48 uncited non-feature files with recorded reasons → status complete.

## Boundaries
Adopt the feature lifecycle, observer/dedupe primitives, API wrapper contracts, hotfix channel, query/URL algebras, linkify/author/text round-trip plane, and widget-controller sequences — they are host-agnostic harness mechanics. Adapt all selectors, GitHub-specific page detection (`github-url-detection`), error copy, DOM class conventions, calver version parsing, and heat-ladder polarity to your target site. Omit the 300 feature implementations themselves (product surface), the Svelte options UI internals and the Safari app shell beyond the bridge facade (host-specific), and the deprecated `deduplicate` loader option (superseded by caller-ID marks).

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`altered-click-delegation.md`](./altered-click-delegation.md)
- [`api-graphql-wrapper.md`](./api-graphql-wrapper.md)
- [`api-rest-wrapper.md`](./api-rest-wrapper.md)
- [`async-event-loop.md`](./async-event-loop.md)
- [`async-micro-kit.md`](./async-micro-kit.md)
- [`attach-element-insertion.md`](./attach-element-insertion.md)
- [`background-message-router.md`](./background-message-router.md)
- [`bisect-debugging.md`](./bisect-debugging.md)
- [`boot-manifest-esm-bootstrap.md`](./boot-manifest-esm-bootstrap.md)
- [`caller-id-dedupe.md`](./caller-id-dedupe.md)
- [`click-all-batching.md`](./click-all-batching.md)
- [`comment-author-text-extraction.md`](./comment-author-text-extraction.md)
- [`commit-message-trailer-normalization.md`](./commit-message-trailer-normalization.md)
- [`compare-url-parsing.md`](./compare-url-parsing.md)
- [`conversation-lock-resolution-ladder.md`](./conversation-lock-resolution-ladder.md)
- [`css-is-not-selector-builder.md`](./css-is-not-selector-builder.md)
- [`delete-branch-feature-anatomy.md`](./delete-branch-feature-anatomy.md)
- [`dom-editing-micro-kit.md`](./dom-editing-micro-kit.md)
- [`dom-first-ttl-value-cache.md`](./dom-first-ttl-value-cache.md)
- [`element-removal-promise.md`](./element-removal-promise.md)
- [`error-funnel-reporting.md`](./error-funnel-reporting.md)
- [`extensible-nav-store-tab-store.md`](./extensible-nav-store-tab-store.md)
- [`extension-ops-helpers.md`](./extension-ops-helpers.md)
- [`feature-loader-lifecycle.md`](./feature-loader-lifecycle.md)
- [`field-input-event-guard.md`](./field-input-event-guard.md)
- [`github-file-url.md`](./github-file-url.md)
- [`gitref-resolution.md`](./gitref-resolution.md)
- [`heat-index-scale.md`](./heat-index-scale.md)
- [`history-deduplicator.md`](./history-deduplicator.md)
- [`host-widget-controllers.md`](./host-widget-controllers.md)
- [`hotfix-channel.md`](./hotfix-channel.md)
- [`hotkey-registration.md`](./hotkey-registration.md)
- [`link-loss-prevention.md`](./link-loss-prevention.md)
- [`observe-leaf-resolve-container.md`](./observe-leaf-resolve-container.md)
- [`options-rename-migrations.md`](./options-rename-migrations.md)
- [`page-fetch-network.md`](./page-fetch-network.md)
- [`pr-merge-detection-ladder.md`](./pr-merge-detection-ladder.md)
- [`pr-reference-parsing.md`](./pr-reference-parsing.md)
- [`preserve-scroll-anchor.md`](./preserve-scroll-anchor.md)
- [`react-controlled-input-writers.md`](./react-controlled-input-writers.md)
- [`react-page-update-signal.md`](./react-page-update-signal.md)
- [`readme-feature-metadata-parser.md`](./readme-feature-metadata-parser.md)
- [`repo-permission-capability-cache.md`](./repo-permission-capability-cache.md)
- [`route-context-url-algebra.md`](./route-context-url-algebra.md)
- [`run-conditions.md`](./run-conditions.md)
- [`safari-companion-bridge.md`](./safari-companion-bridge.md)
- [`safe-tab-options-open.md`](./safe-tab-options-open.md)
- [`search-query-mutator.md`](./search-query-mutator.md)
- [`selector-fixture-registry.md`](./selector-fixture-registry.md)
- [`selector-observer.md`](./selector-observer.md)
- [`singleton-init-lifecycle.md`](./singleton-init-lifecycle.md)
- [`spa-navigation-url-store.md`](./spa-navigation-url-store.md)
- [`storage-byte-accounting-polyfill.md`](./storage-byte-accounting-polyfill.md)
- [`text-linkify-pipeline.md`](./text-linkify-pipeline.md)
- [`text-number-formatting-kit.md`](./text-number-formatting-kit.md)
- [`toast-progress.md`](./toast-progress.md)
- [`token-identity-gate.md`](./token-identity-gate.md)
- [`tooltip-component.md`](./tooltip-component.md)
- [`url-hash-replacestate-cleanup.md`](./url-hash-replacestate-cleanup.md)
- [`whitespace-visualizer.md`](./whitespace-visualizer.md)
