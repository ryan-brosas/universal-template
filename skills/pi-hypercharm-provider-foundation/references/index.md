<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->

# Pi-Hypercharm-Provider: Provider Extension Foundation (SWR Catalog + Telemetry Status Line)

## Use this for
Build a coding-agent provider extension that registers an OpenAI-completions-compatible endpoint with a self-updating model catalog and a spend/quota footer. The repo serves a zero-latency stale model list (cache → embedded), revalidates against the live catalog in the background, and hot-swaps via one provider-config factory; per-request fetch interception tees each chat-completions stream to capture usage cost and rate-limit headers without touching the SDK's copy; lifecycle events gate every poll so sessions that never use the provider make zero status API calls, while the balance still ticks down live between polls via overwrite-reconciled optimistic spend; a pure presentation module renders a two-zone, width-aware status line with progressively compressing tiers. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval. The status module ships a dependency-free smoke suite (`node tests/status.smoke.ts`, GREEN on Node 26.7.0 at HEAD `4520704`) — display-layer capsules are test-pinned, runtime-event capsules carry explicit coverage caveats.

## Load the matching source dump
- `./swr-model-sync.md` — serve-stale → background-revalidate → hot-swap ladder; registration never awaits the network; abort-on-new-session.
- `./merge-precedence-model-pipeline.md` — base → patch.json → custom-models.json composition, per-field patch merges, post-patch sanitation deletes for non-reasoning models.
- `./deprecated-model-graveyard.md` — delisted models tombstoned with `deprecatedAt`, 14-day grace, resurrection on return, clock never resets.
- `./teed-usage-capture.md` — per-request fetch interception + `response.body.tee()` SSE scanner; pending-state commit after tees settle; never patch globalThis.fetch.
- `./tee-reader-barrier.md` — self-cleaning promise set + `allSettled` drain so turn_end commits pendings only after every teed scan finished (both settle paths release).
- `./account-fetch-null-ladder.md` — never-throw `fetchJsonGet` with 8s timeout composition; stamp-then-await single-flight credits throttle; learn-only one-shot meta latch.
- `./settled-event-polling-gate.md` — poll only at `agent_settled`, activity-gated; single-flight throttled credits fetch; turn_end pending-commit accounting.
- `./ansi-width-math.md` — visible-column counting over ANSI/emoji/ambiguous-width glyphs; truncation reserving the ellipsis column.
- `./tiered-status-widget.md` — left-preserving/right-degrading two-zone render that is ALWAYS exactly terminal width.
- `./hc-number-formatting.md` — `trimZeros` core plus three deliberately asymmetric magnitude ladders (balance compacts ≥10k, rate exact-until-1k, spend widens precision down to `~0`); smoke-pinned.
- `./config-coercion-persistence.md` — field-by-field JSON coercion onto defaults; read-merge-write persistence preserving foreign keys.
- `./config-value-resolution.md` — pi credential semantics: `!command` / `$VAR` interpolation with escapes and all-or-nothing failure.
- `./status-command-surface.md` — `/hypercharm-status` token grammar + interactive cycling menu: write→render→confirm on every accept, one usage string for every reject, headless prints summary instead of opening menus.
- `./thinking-level-mapping.md` — provider reasoning enums → total seven-level map with explicit nulls; clamp-then-omit request conversion.
- `./catalog-model-transform.md` — strict-zero catalog→model-record projection plus fixed compat block; id-less entries rejected.
- `./activity-gated-visibility.md` — no half-empty glare: render only after first provider activity; defensive model-getter access; slot merging/clearing.
- `./abort-lifecycle-out-of-credits.md` — dual AbortControllers replaced each session_start; aborted+epoch check before hot-swap; once-per-session 402 notify with forced balance refetch.
- `./optimistic-balance-deduction.md` — deduct observed turn spend from the last polled balance between polls; safe only because every poll OVERWRITES (never adjusts) `balance`; null stays unknown; estimates clamp at 0 and never signal real exhaustion. Smoke-pinned.
- `./stale-ctx-epoch-guard.md` — session-replacement safety for async continuations: epoch captured before await + narrow stale-message swallow so a refresh racing /new//fork can't crash pi.
- `./cache-pricing-field-remap.md` — cached-output price ⇒ host `cacheRead`, cached-input price ⇒ host `cacheWrite`; offline generator and runtime transform must invert together (49f661b erratum).
- `./runtime-auth-key-plumbing.md` — single-writer `cachedApiKey` resolved once per session from pi's ModelRegistry; `$HYPERCHARM_API_KEY` registration placeholder vs real-key-at-call-time split; synchronous three-source fail-fast throw.
- `./stream-simple-delegation-adapter.md` — namespaced custom api name so `streamSimple` never shadows the host builtin; per-call model normalization (family/baseUrl forcing), reasoning option rest-strip, injectable upstream fetch seam.
- `./sync-run-choreography.md` — offline catalog-sync main(): loud-fail CLI posture vs runtime null-ladders, shape-tolerant fetch, graveyard-before-overwrite ordering, wholesale models.json rewrite (curated-preserve comment is vestigial), diff summary.
- `./custom-model-upstream-promotion-prune.md` — custom models promoted upstream are REMOVED from the overlay file, with in-place array refresh before README composition.
- `./on-disk-json-conventions.md` — script writes loud / runtime writes fail-soft; reads degrade by shape (`{}` records, `Array.isArray` lists); uniform two-space+newline serializer everywhere.

## Capsule map
- **Catalog sync** — `swr-model-sync.md`: `loadStaleModels`/`revalidateModels` — disk cache merged with embedded as instant base; live fetch (8s cap) merges and caches; failed paths return null and keep serving stale; swap goes through one `makeProviderConfig()` factory so handler and list never desync.
- **Merge pipeline** — `merge-precedence-model-pipeline.md`: `buildModels`/`applyPatch`/`withDeprecated` — custom > patch > base per model, cost subfields fall back individually, non-reasoning models get thinkingFormat/thinkingLevelMap stripped and emptied compat deleted.
- **Grace period** — `deprecated-model-graveyard.md`: `updateDeprecatedModels` — reconcile-before-overwrite state machine (add/resurrect/evict); unparseable stamps count expired; runtime replays graveyard minus metadata.
- **Usage tee** — `teed-usage-capture.md`: `metaFetch`/`readUsageFromTee` — URL-scoped interceptor counts requests, captures x-ratelimit headers, flags 402, tees body; partial-line-safe SSE scan; all errors swallowed, lock always released.
- **Settle barrier** — `tee-reader-barrier.md`: `trackTeeReader`/`settleTeeReaders` (`index.ts:483-496`) — promise set self-cleans on both fulfill and reject; turn_end awaits an `allSettled` snapshot before committing pendings, so aborted main streams can never wedge or reject the commit.
- **Account fetch** — `account-fetch-null-ladder.md`: `fetchJsonGet`/`refreshCredits`/`refreshAccountMeta` (`index.ts:623-695`) — HTTP≠2xx/network/timeout all collapse to `null`; 8s timeout composed with session abort via `AbortSignal.any`; credits stamped-before-await with single-flight; meta latches only when something was learned; balance writes are REPLACEMENTS (the optimistic-spend safety contract).
- **Polling gate** — `settled-event-polling-gate.md`: five-event wiring — prefetch only when provider active, commit pendings at turn_end after `settleTeeReaders()`, re-poll only at agent_settled under an activity gate.
- **Optimistic balance** — `optimistic-balance-deduction.md`: `applyOptimisticSpend` (`status.ts:106-110`, smoke-pinned) called from `commitPending` (`index.ts:802-828`) — per-turn spend ticks the footer balance live between ≥15s-apart polls; overwrite-reconciliation makes it double-count-free.
- **Stale-ctx guard** — `stale-ctx-epoch-guard.md`: `statusEpoch`/`isStaleCtxError`/`updateStatusAfter` (`index.ts:713-734`) — epoch-capture-before-await vetoes obsolete continuations; narrow message-substring swallow is the render-side net.
- **Width math** — `ansi-width-math.md`: `termVisWidth`/`truncateAnsi` — CSI sequences free, Emoji_Presentation = 2, ambiguous set host-tuned (◆ deliberately narrow), truncate at maxCols−1 plus "…".
- **Status widget** — `tiered-status-widget.md`: `StatusLineWidget.render`/`buildAccountTiers` — first fitting tier wins, exact-width justification guaranteed by test, warn gem+color flip, dedupe adjacent tiers.
- **Config** — `config-coercion-persistence.md`: `coerceStatusConfig`/`writeStatusConfig` — per-field fallbacks (null/false both disable), writes preserve unknown keys, failed write leaves memory config applied.
- **Credentials** — `config-value-resolution.md`: `resolveConfigValue` — auth.json beats env; `$$`/`$!` escapes; unset var ⇒ whole value undefined; commands shell out with 10s timeout.
- **Command surface** — `status-command-surface.md`: `handleStatusCommand`/`configureStatusInteractive`/`statusSummary` (`index.ts:830-1010`) — closed-set token grammar, write→render→confirm per accepted leg, single usage string on rejects, headless summary fallback; interactive menu cycles modes and splices custom low-balance presets in order.
- **Thinking levels** — `thinking-level-mapping.md`: `buildThinkingLevelMap`/`ON_OFF_THINKING_LEVEL_MAP` — levels array ⇒ identity map, bare `can_reason` ⇒ off/max boolean map, `"none"` dual spelling; request side clamps then omits "off".
- **Catalog transform** — `catalog-model-transform.md`: `transformApiModel` — null on missing id, zeros for absent numbers, attachments ⇒ text+image, fixed compat defaults (supportsStore false, deepseek format, max_tokens field).
- **Cache pricing remap** — `cache-pricing-field-remap.md`: `transformModel`/`transformApiModel` cost block (`index.ts:285-290`, script twin `:255-262`) — `cacheRead` = cached-OUTPUT price, `cacheWrite` = cached-INPUT price; twins must change together (49f661b inversion).
- **Visibility** — `activity-gated-visibility.md`: try/catch around the throwing ctx.model getter, clearAll on foreign provider, combined statusbar slots.
- **Number formatting** — `hc-number-formatting.md`: `trimZeros`/`formatBalHc`/`formatSpendHc`/`formatRateCompact` (`status.ts:114-144`, smoke-pinned `tests/status.smoke.ts:27-39`) — balance compacts ≥10k, rate exact-until-1k, spend never compacts but widens precision down to `"~0"`; flattening the asymmetry is the porting mistake.
- **Cancellation & alerts** — `abort-lifecycle-out-of-credits.md`: dual AbortControllers replaced each session_start (+ epoch bump), aborted+epoch check before hot-swap, once-per-session 402 notify with forced balance refetch.
- **Auth plumbing** — `runtime-auth-key-plumbing.md`: `cachedApiKey`/`resolveApiKey` (`index.ts:420-425`) — one writer (ModelRegistry at session_start), five readers; registration carries `$HYPERCHARM_API_KEY` placeholder while requests use the runtime cache or throw with all three remediation paths.
- **Delegation adapter** — `stream-simple-delegation-adapter.md`: `streamHypercharm` frame (`index.ts:570-619` minus tee/clamp interiors) — `"hypercharm"` api name is handler namespacing; normalize to `openai-completions`, strip raw `reasoning` after conversion, `options.fetch ?? globalThis.fetch` injection seam.
- **Sync choreography** — `sync-run-choreography.md`: update-models.js `main()` (:407-527) — exit(1) pre-flight key gate, non-2xx throws w/ HTTP status, array|models|data shape tolerance, graveyard reconcile BEFORE wholesale models.json overwrite; existingModelsMap is dead code.
- **Promotion prune** — `custom-model-upstream-promotion-prune.md`: custom-models.json ids intersected against upstream (:462-480); duplicates deleted + file rewritten + in-memory array refreshed in place before README build.
- **JSON on disk** — `on-disk-json-conventions.md`: loadJson `{}` degradation vs saveJson throw (script), cacheModels/writeStatusConfig silent twins (runtime), 2-space+`\n` uniformity.

## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
pi-hypercharm-provider (MIT), `main@4520704` (pass-4 deep pass 2026-08-25; prior pin `0bdfab4` → pass-3 drift re-entry to `4520704`); Codebase Memory project `pi-hypercharm-provider` (261 nodes / 689 edges, full mode, indexed 2026-08-24T14:05Z generation; index HEAD == checkout HEAD verified at pass start; zero parse_partial/skipped). Display layer test-pinned by `tests/status.smoke.ts`; runtime/event/script paths have no upstream tests — those capsules record deterministic source-read probes and coverage caveats. Pass 1: initial 13-capsule sweep. Pass 2: symbol-granular citation-vs-inventory sweep added the tee-reader barrier, account-fetch null ladder, status command surface, and number-formatting capsules. Pass 3: origin-fetched pin poll found +20-commit drift → mined optimistic balance deduction (`3a25ba3`), stale-ctx epoch guard (`82de131`), and cache-pricing inversion (`49f661b`) into three new capsules; all pre-existing refs re-pinned with errata where drift invalidated recorded semantics. Pass 4 (this pass): whole-file deep-learning squeeze over all four code files mined five uncited seams (runtime auth plumbing, streamSimple delegation adapter frame, sync-run choreography incl. two dead-code findings, custom-model promotion prune, on-disk JSON conventions) plus a convertPricing dead-code erratum in catalog-model-transform.md; work record created at inspo/pi-hypercharm-provider-work/.

## Full view (memory graph)
Revalidate `pi-hypercharm-provider` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root `/mnt/hdd/utopia/inspo/pi-hypercharm-provider` — a LIVE SYMLINK into canonical `/mnt/hdd/utopia/inspo/pi-ecosystem/pi-hypercharm-provider`, so refresh-in-place works (no twin adoption needed) — branch main, commit `4520704`, mode full, 261 nodes / 689 edges, generation 2026-08-24T14:05:13Z, exclusions `.git`/`node_modules` by design; pass 4 re-verified root/HEAD/pin match live plus `no_recorded_issue` coverage on all four code files (`index.ts`, `status.ts`, `scripts/update-models.js`, `tests/status.smoke.ts`). Source and direct tests decide shipped claims.

## Boundaries
Adopt pure contracts: SWR ladder shape, merge precedence, graveyard state machine, tier rendering, width math, coercion rules, resolver semantics. Adapt host integration points: event names (`session_start`/`model_select`/`turn_end`/`agent_settled`/`session_shutdown`), UI slot API, cache/config paths, AMBIGUOUS_WIDE glyph set, throttle budgets. Omit product behavior: hyper.charm.land endpoints and hypercredit units (20 hc ≈ $1 observed), Charm catalog field names, the README-generation surface of update-models.js beyond its reconciliation logic.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`abort-lifecycle-out-of-credits.md`](./abort-lifecycle-out-of-credits.md)
- [`account-fetch-null-ladder.md`](./account-fetch-null-ladder.md)
- [`activity-gated-visibility.md`](./activity-gated-visibility.md)
- [`ansi-width-math.md`](./ansi-width-math.md)
- [`cache-pricing-field-remap.md`](./cache-pricing-field-remap.md)
- [`catalog-model-transform.md`](./catalog-model-transform.md)
- [`config-coercion-persistence.md`](./config-coercion-persistence.md)
- [`config-value-resolution.md`](./config-value-resolution.md)
- [`custom-model-upstream-promotion-prune.md`](./custom-model-upstream-promotion-prune.md)
- [`deprecated-model-graveyard.md`](./deprecated-model-graveyard.md)
- [`hc-number-formatting.md`](./hc-number-formatting.md)
- [`merge-precedence-model-pipeline.md`](./merge-precedence-model-pipeline.md)
- [`on-disk-json-conventions.md`](./on-disk-json-conventions.md)
- [`optimistic-balance-deduction.md`](./optimistic-balance-deduction.md)
- [`runtime-auth-key-plumbing.md`](./runtime-auth-key-plumbing.md)
- [`settled-event-polling-gate.md`](./settled-event-polling-gate.md)
- [`stale-ctx-epoch-guard.md`](./stale-ctx-epoch-guard.md)
- [`status-command-surface.md`](./status-command-surface.md)
- [`stream-simple-delegation-adapter.md`](./stream-simple-delegation-adapter.md)
- [`swr-model-sync.md`](./swr-model-sync.md)
- [`sync-run-choreography.md`](./sync-run-choreography.md)
- [`tee-reader-barrier.md`](./tee-reader-barrier.md)
- [`teed-usage-capture.md`](./teed-usage-capture.md)
- [`thinking-level-mapping.md`](./thinking-level-mapping.md)
- [`tiered-status-widget.md`](./tiered-status-widget.md)
