<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->

# ESLint Foundation

## Use this for
Building a lint rule engine or flat-config linter: the verify pipeline from raw text to executed rules, config normalization and caching, worker-scaled file discovery, the autofix loop, disable-directive suppression, a RuleTester harness, AST rule primitives, and the code-path-analysis kernel (fork contexts, segment graphs, loop/try/switch state machines). Pass 3 adds the fix-command factory + BOM-slicing sweep, retained-range fix composition, char-source code-unit mapping, shared traverser break semantics, serializability/dup detection, tester failure-location estimation, feature flags, worker cloneability, concurrency economics, the suppressions ledger, sync parse/preprocess boundaries, redundant-inline-config detection, schema-shape resolution, message interpolation, traversal instance caching, severity/stats, grapheme measurement, naming grammar, context prototype extension, directive predicates, regex-flag probes, reachability, lazy rule maps, timing merge/display, emission-order conformance, static string extraction, and the full tester trap/suggestion/config/runner planes. Pass 6 adds the TokenStore cursor navigation + location-index algebra, SourceCode offset⇄location conversion, the Language plugin declaration contract, and Config serialization / rule-language compatibility gates. Pass 7 adds the verify-tail suppression split and its autofix-loop interplay, the schema-driven cross-config merge table (rules severity-splice, cycle-safe deepMerge with pair memoization, plugins redefine guard, eslintrc trap keys), SourceCode scope acquisition + mixed-lifetime caches, and the CLI/runtime-info translation planes. Pass 11 adds the constructor engine bundle + options-or-URL duality, results-instance binding (foreign-results TypeError), the completed poor-concurrency notice trichotomy, and the result-cache reconcile/write-ownership plane. Source and tests are authoritative; the capsule contract is the loadable dump for reuse.

## Load the matching source dump
- `./verify-pipeline.md` — normalize any config to a FlatConfigArray, resolve per-file config, route processor vs plain verify.
- `./autofix-loop.md` — non-overlapping fix application, convergence cap, circular-fix detection.
- `./bom-slicing-fix-sweep.md` — applyFixes sort-once/sweep-once mechanics, BOM slicing, defer-don't-merge conflicts.
- `./rule-fixer-command-factory.md` — RuleFixer command constructors, type-check-at-creation vs overlap-check-at-application split.
- `./fix-tracker-retained-ranges.md` — FixTracker union ranges so one rule's multi-edit fix claims its span against siblings.
- `./rule-execution.md` — rule listener assembly, report-metadata enforcement, esquery selector traversal.
- `./traversal-instance-caching.md` — per-Language WeakMap instances with per-call state rebuild; the cross-file bleed trap.
- `./emission-order-conformance.md` — the assertEmissions test machinery pinning selector dispatch order incl. TS visitor keys.
- `./inline-config.md` — severity-only inline override that retains configured options.
- `./redundant-inline-config-detection.md` — unused-inline-config messages backed by strict option deep-compare.
- `./disable-directives.md` — mark-then-split suppression model and unused-directive reporting.
- `./inline-config-comment-gate.md` — the shared directivesPattern allowlist + SourceCode.getInlineConfigNodes cache feeding both the disable-directives and applyInlineConfig planes.
- `./directive-recognition-predicates.md` — directive-prologue position grammar, range-shared ancestor climb, comment prefix tables.
- `./config-normalization.md` — base-config layering, error-index rebasing, eager rule validation.
- `./config-loader-caching.md` — promise-first two-level config cache with mtime-based reload.
- `./file-discovery-workers.md` — stat-first pattern partitioning plus cache-aware worker-count decision.
- `./net-linting-ratio-concurrency.md` — netLintingDuration accounting, min-of-workers ratio, pre-spawn poor-concurrency notice trichotomy + stub seam.
- `./worker-cloneability-gate.md` — structuredClone probe, per-key diagnosis, coded error, symbol escape hatch.
- `./worker-file-claim-loop.md` — brokerless fixed-workload pool: one 4-byte SharedArrayBuffer atomic counter as the only sync point, index-tagged results reassembled into original file order.
- `./worker-timing-accumulators.md` — netLintingDuration decomposition: three bigint accumulators subtract config-load and file-read costs so only parallelizable lint computation reaches the concurrency notice.
- `./constructor-options-or-url-duality.md` — one-shot WeakMap engine-bundle factory; raw-options-vs-module-URL duality across the thread boundary with cloneability bypass symbol; construction-time .eslintignore warning.
- `./results-instance-binding.md` — getRulesMetaForResults fail-loud foreign-results TypeError, <text>→placeholder normalization before config lookup, unknown-rule silent skip.
- `./result-cache.md` — three-condition cache validity, versioned config hashing, no-fixed-output guard, update-existing-only writes, single run-tail reconcile.
- `./rules-and-tester.md` — RuleTester wrapper-rule freezing, AST-immutability sentinel, fix re-linting.
- `./tester-trap-harness.md` — parser wrapping w/ start/end getter throws, forbidden-method WeakSet interception, fatal-in-fix re-verification.
- `./tester-config-assembly.md` — case-properties-as-config layering, copy-parsers/share-proxy split, ajv two-step validation.
- `./tester-runner-shims.md` — describe/it/only accessor chain across Mocha/Vitest/plain-node; assertionOptions tightening knobs.
- `./tester-suggestion-ladder.md` — full per-suggestion contract: uniqueness by rendered desc, data rehydration, output differs-from-source.
- `./test-location-estimator.md` — stack-rebuilt "roughly at valid[3]" frames via caller-file re-read and brace-depth scan.
- `./cycle-aware-dup-detection.md` — path-scoped serializability check + top-level-strip stable-stringify duplicate detection.
- `./ast-primitives.md` — static property names, parenthesisation checks, tracked multi-fixes, lazy rule maps.
- `./static-string-extraction.md` — getStaticStringValue Literal/TemplateLiteral disambiguation ladder.
- `./char-source-code-units.md` — string/template value chars → raw source spans through escapes, surrogates, continuations.
- `./schema-shape-resolution-ladder.md` — meta.schema array/object/false/absent → one validator contract; {}-is-a-no-op rejection.
- `./default-options-deep-merge.md` — positional defaultOptions merge with null-vs-undefined semantics and array atomicity.
- `./message-interpolation-contract.md` — {{ token }} substitution, preserve-on-missing, fresh /g regex discipline, unsubstituted detection.
- `./severity-stats-normalization.md` — 0/1/2 ⇄ off/warn/error dual normalizers; fatal-first stats classification.
- `./lazy-rule-map-freeze.md` — thunk registry, debug-only countdown wrapper, prototype-frozen writes, iterator redirection.
- `./cpa-analyzer-orchestration.md` — CodePathAnalyzer event interleaving around an existing AST traversal.
- `./cpa-fork-context.md` — parallel-lane matrix (row×column) with finally count-doubling and merge rules.
- `./cpa-segment-lazy-attachment.md` — used-flag lazy edge attachment, unused-segment flattening, unreachable-tail retention.
- `./cpa-choice-contexts.md` — shared fork/merge algebra for &&, ||, ??, if/ternary, and optional chaining.
- `./cpa-try-finally-lanes.md` — try/catch/finally lane-doubling, half-split head routing, first-throwable wiring.
- `./cpa-loop-contexts.md` — five loop grammars sharing break/continue wiring with per-grammar continue targets.
- `./cpa-switch-default-rewiring.md` — mid-switch default disconnect-and-reloop plus empty-default re-homing.
- `./cpa-codepath-surface.md` — finished-path read API and cycle-safe ordered traversal with skip/break control.
- `./segment-reachability-predicate.md` — isAnySegmentReachable: the empty-set⇒false oracle over CPA segments.
- `./shared-traverser-break-semantics.md` — generic enter/leave walker: unknown-type degradation, leave-after-break, parents() copy.
- `./report-normalization-pipeline.md` — report descriptor → validated LintMessage with merged fix + suggestions.
- `./inline-config-merge-ladder.md` — inline severity splice retaining file-level options; duplicate/unused/invalid triage.
- `./unused-directive-reporting.md` — used-on-first-suppression, reverse enable-liveness walk, format-preserving removal fixes.
- `./vfile-context-identity.md` — virtual/physical path pair, BOM dual-representation, frozen prototype-chained rule contexts.
- `./context-prototype-extension.md` — FileContext.extend via Object.create+frozen base; own-enumeration caveat.
- `./selector-parse-specificity.md` — memoized selector parsing, nodeType extraction, three-key specificity ordering.
- `./sync-parse-preprocess-boundary.md` — ParserService/ProcessorService ok-envelopes, thenable refusal, canonical fatal shapes.
- `./suppressions-ledger.md` — violation baselines: ≤-count admission, surplus credit, prune GC, POSIX path keys.
- `./feature-flag-ladder.md` — active/inactive flag tables with replacedBy tri-state (forward/warn/throw) + env merge.
- `./rule-timing-harness.md` — zero-cost-when-disabled per-rule timing with worker merge + exit-hook display.
- `./timing-merge-display.md` — TIMING env grammar, additive cross-process totals, suppression guards, sorted table.
- `./grapheme-measurement-styling.md` — ASCII fast-path grapheme counting + strip-then-measure ANSI table alignment.
- `./scoped-naming-grammar.md` — normalizePackageName shorthand/scoped/backslash resolution order and -|$ boundary.
- `./unicode-flag-probe.md` — regexpp-based would-this-be-valid-under-u/v probe with version clamps and catch-to-false.
- `./verify-options-error-attribution.md` — three-layer option normalization ladder; file→line→rule error decoration.
- `./processor-routing-reconf.md` — processor detection, supportsAutofix gating, changed-content recursive re-config.
- `./id-generator-visitor-primitives.md` — wrap-safe 32-bit id counter; multi-subscriber event-name registry.
- `./rule-options-pipeline.md` — schema forms, validator caching, defaultOptions deep-merge.
- `./novar-hoisted-call-order-guard.md` — var→let autofix veto when a hoisted FunctionDeclaration is CALLED before the declaration (call-order TDZ hazard #21213).
- `./nolop-zero-underflow-gate.md` — zero-underflow classifier: falsiness-gate removal + all-zero-coefficient test distinguishes `5e-324` from `1e-324` (#21218).
- `./token-store-cursor-navigation.md` — option grammar (number/function/object) + filter→skip→limit decorator order; count=0 vs absent; exclusive between-windows; adjacent-run comment APIs.
- `./token-store-index-map.md` — endpoint→token-index hash map with comments pointing at their NEXT token; ±1 boundary corrections; sorted-comments binary search; fully-contained commentsExistBetween.
- `./source-code-text-loc-lines.md` — newline-only line table (backtracking war story), upper-bound binary search, paired past-end special cases, exact offset⇄{line,column} symmetry.
- `./js-language-declaration.md` — Language plugin contract: static descriptor fields, options validate/normalize hooks, non-throwing ok-envelope parse, deferred scope analysis, esquery class suffix matching.
- `./config-serialization-processor-binding.md` — resolved-object + private-string-id dual binding; parent-short-circuiting function-refusing JSON projection of languageOptions/plugins/processor.
- `./rule-language-compatibility-gate.md` — meta.languages wildcard/namespace match ladder at config time; disabled-rule bypass; single aggregated unsupported-language error.
- `./suppression-split-verify-tail.md` — one partition point at the verify tail: suppressed problems park in a last-run-only internal slot; autofix passes never see them.
- `./rules-cross-config-merge.md` — rules merge across config-array elements: normalize-and-clone everything, severity-only splice onto first parent's options, otherwise second wins.
- `./deep-merge-cycle-memo.md` — deepMerge pair memoization registered before recursion so self-/cross-referencing configs terminate; undefined restores first; arrays atomic.
- `./eslintrc-key-rejection.md` — generated always-throw schemas over the exact ten trap keys; messageTemplate-classifiable errors; plugins-array eslintrc special case.
- `./source-code-scope-cache.md` — getScope parent-climbing acquire with Program-only inner=false, function-expression-name hop, WeakMap per-node memo; mixed cache lifetimes.
- `./cli-options-translation-ladder.md` — pure optionator→ESLintOptions projection: tri-state overrideConfigFile, quiet×maxWarnings coupling, two-predicate fix policy, --ext glob synthesis.
- `./runtime-info-env-report.md` — per-invocation closure-cached command probes, "Not found"/"(Currently used)" ladder, fail-hard decorated rethrow.
- `./lintfiles-pattern-collapse-and-tail.md` — lintFiles pre-flight collapse/throw/passOnNoPatterns, stale-cache unlink swallow, reconcile→suppress→decorate tail order.
- `./fix-types-filter-composition.md` — fix×fixTypes AND-composed fixer; directive pseudo-type; meta.type-less rules never fixed under active fixTypes.
- `./per-file-read-retry-abort.md` — per-file gate ladder: config gate, cache short-circuit except fix-reprocess, timed signal-gated read, abort-after-read, ENFILE/EMFILE retry, shared-controller abort.
- `./vertext-placeholder-duality.md` — `<text>`⇄placeholder swap for config resolution; config-driven filterCodeBlock adoption; conditional output/source attachment.
- `./ignored-result-taxonomy.md` — four configStatus-keyed ignore messages with remediation hints; per-call warnIgnored overrides the constructor value both ways.
- `./deprecated-rules-lazy-getter.md` — lazy usedDeprecatedRules getter descriptor; Config-keyed WeakMap frozen memo; never persisted into the cache file.
- `./report-postprocessing-twins.md` — outputFixes validate-while-filtering writes; getErrorResults non-mutating error-only projection with fixableErrorCount preserved.
- `./eslint-options-error-accumulation.md` — fail-all processOptions: 13 removed-key migration hints + type checks in ONE ESLintInvalidOptionsError.
- `./warning-service-dedup-plane.md` — one injectable emitter, five typed warning channels, non-Node no-op fallback; workers stub exactly the two channels the controlling thread always emits.
- `./default-config-lazy-proxy.md` — frozen 4-element default config; rules Proxy forwarding get/has into the LazyLoadingRuleMap so built-ins stay unloaded until named; reference-shared tester variant without default ignores.

## Capsule map
- **Verify pipeline** — `verify-pipeline`: duck-typed config-array reuse → placeholder-filename lookup → processor/plain routing; suppressed messages, never dropped. `report-normalization-pipeline`: one `context.report()` descriptor → validated LintMessage with merged fix, suggestions, 1-based locations. `processor-routing-reconf`: preprocess→per-block lint→postprocess routing, supportsAutofix gating, extracted blocks resolving their OWN config via recursive re-config (legacy passthrough otherwise). `verify-options-error-attribution`: verify options normalize to one shape; traversal failures name file, line, and rule. `vfile-context-identity`: processor-created virtual files keep disk identity; per-rule contexts stay cheap via prototype chain.
- **Autofix** — `autofix-loop`: range-sorted non-overlap sweep, 10-pass cap, second-previous-text cycle detection, post-loop re-verify. `bom-slicing-fix-sweep`: NEGATIVE_INFINITY sentinel, BOM idiom via negative ranges, fixed:true-on-conflict loop economics. `rule-fixer-command-factory`: {range,text} commands, eager type-check only. `fix-tracker-retained-ranges`: union-expansion fixes with verbatim tail/head re-splice.
- **Rule execution** — `rule-execution`: frozen shared context, report-time fixable/suggestions enforcement, specificity-ordered enter/exit traversal with ancestry discipline. `traversal-instance-caching`: language-keyed WeakMap, per-call ESQueryHelper rebuild. `emission-order-conformance`: identity-asserted selector order matrix over JSX/TS trees. `selector-parse-specificity`: memoized selector parsing, nodeType candidate extraction, three-key specificity ordering.
- **Inline configuration** — `inline-config`: inline `[severity]` splices under it the file-config options; skip-revalidation gate. `redundant-inline-config-detection`: two-message redundancy ladder over strict containsDifferentProperty compare. `inline-config-merge-ladder`: severity spliced while KEEPING file-level options; duplicate/unused/invalid triage ladder; revalidation skipped when config object identity is unchanged. `inline-config-comment-gate`: one shared directivesPattern allowlist + cached getInlineConfigNodes selection feed BOTH the disable-directives and applyInlineConfig planes; Line comments restricted to the disable family; Shebangs never.
- **Suppression** — `disable-directives`: line directives desugar to enable/disable pairs; suppressions annotate problems for later splitting; whitespace-preserving unused-directive fixes. `directive-recognition-predicates`: prologue position grammar + range-climb + prefix tables. `suppressions-ledger`: committed violation baselines with all-or-nothing admission and prune GC. `unused-directive-reporting`: prove a disable was unnecessary and emit a whitespace-preserving removal fix.
- **Config model** — `config-normalization`: unshifted base config, localized error indices, construction-time rule validation, numeric severity normalization. `schema-shape-resolution-ladder`: four meta.schema forms to validator-or-null; {} rejected as no-op. `default-options-deep-merge`: positional zip, null-wins, arrays atomic.
- **Config loading** — `config-loader-caching`: promise-seeded maps dedupe concurrent lookups; sync getter throws on pending entries; mtime query reloads changed configs.
- **File discovery & scaling** — `file-discovery-workers`: files/dirs/globs partition by stat, ignores come from the config loader, auto workers = ceil(files/50) capped at cores/2, ≤1 ⇒ inline. `net-linting-ratio-concurrency`: (lint−IO)/wall per worker, min-of-workers < 0.7 ⇒ actionable hint. `worker-cloneability-gate`: ESLINT_UNCLONEABLE_OPTIONS with minimal key naming + symbol bypass for options modules. `worker-file-claim-loop`: one 4-byte SharedArrayBuffer atomic counter is the only synchronization point; each worker claims files via Atomics.add until undefined; index-tagged results slot into a preallocated array so out-of-order completion still yields original file order. `worker-timing-accumulators`: netLintingDuration = lintingDuration − loadConfigTotalDuration − readFileCounter.duration — config-load and file-read costs are measured separately (bigint) and subtracted so only CPU-bound lint computation drives the ratio notice.
- **Result caching** — `result-cache`: valid iff present ∧ unchanged ∧ config-hash match; never cache fixed output; null-source reread sentinel.
- **Rule testing** — `rules-and-tester` + `tester-trap-harness` + `tester-config-assembly` + `tester-runner-shims` + `tester-suggestion-ladder` + `test-location-estimator` + `cycle-aware-dup-detection`: frozen options/settings, AST snapshot equality, parser getter-throws, forbidden-method interception, autofix/suggestion re-linting, runner-agnostic shims, tightened assertion knobs, rendered-desc uniqueness, stack-rebuilt failure locations, serializability-gated dup checks. `unicode-flag-probe`: test `u`/`v` pattern validity without executing the regex.
- **AST utilities** — `ast-primitives` + `static-string-extraction` + `char-source-code-units`: value-staticness over syntax, immediate-token parenthesisation, retained-range multi-fix tracking, escape-aware source-span mapping. `segment-reachability-predicate`: empty⇒false liveness oracle. `shared-traverser-break-semantics`: degrade-don't-throw walkers with leave-after-break. `directive-recognition-predicates`: prologue/comment recognition.
- **Options plumbing** — `rule-options-pipeline`: absent/array/object/false schema forms, WeakMap-cached ajv validators, deep-merged defaultOptions, disabled rules skip validation.
- **Messages & presentation** — `message-interpolation-contract`: trim-in-check preserve-on-missing interpolation + unsubstituted detection. `severity-stats-normalization`: dual-spelling severities, fatal-first tallies. `grapheme-measurement-styling`: grapheme counts for limits, stripped-length alignment for colored output. `scoped-naming-grammar`: package name resolution order.
- **Registries & services** — `lazy-rule-map-freeze`: thunk registry with frozen writes and redirected iterator. `sync-parse-preprocess-boundary`: ok-envelope + thenable-refusal facades over plugin surfaces. `feature-flag-ladder`: replacedBy tri-state admission. `context-prototype-extension`: Object.create context views over one frozen base. `id-generator-visitor-primitives`: wrap-safe 32-bit id counter; multi-subscriber event-name registry.
- **Code-path analysis (pass 2)** — `cpa-analyzer-orchestration`, `cpa-fork-context`, `cpa-segment-lazy-attachment`, `cpa-choice-contexts`, `cpa-try-finally-lanes`, `cpa-loop-contexts`, `cpa-switch-default-rewiring`, `cpa-codepath-surface`.
- **Observability** — `rule-timing-harness` + `timing-merge-display`: stats envelope {result,tdiff}; TIMING grammar; additive worker merge; exit-hook sorted table.
- **Core rule drift fixes (pass 5)** — `novar-hoisted-call-order-guard`: var→let autofix vetoes when a hoisted FunctionDeclaration is CALLED (callee position) before the declaration — call order, not textual read order, is the TDZ hazard. `nolop-zero-underflow-gate`: numeric-literal validation must not gate on truthiness; value===0 falls back to an all-zero-coefficient test over the written form to separate `5e-324`/`0e5` from `1e-324`.
- **Token/source/language planes (pass 6)** — `token-store-cursor-navigation`: skip counts POST-filter tokens; `{count:0}` iterates nothing while absent count (-1) is unlimited; between-windows are exclusive of both endpoints. `token-store-index-map`: one hash map over token endpoints; comment entries point at their NEXT token so comment cursors can binary-search the small sorted array instead. `source-code-text-loc-lines`: lineStartIndices point AFTER each ECMA-262 terminator; getLocFromIndex(text.length) and last-line column==length pair up so offset⇄loc round-trips exactly. `js-language-declaration`: parse() never throws — fatal parse errors become {ok:false,errors}; scope analysis defers to createSourceCode unless the parser supplied one. `config-serialization-processor-binding`: runtime Config keeps resolved objects plus private string ids; toJSON refuses functions anywhere under languageOptions. `rule-language-compatibility-gate`: meta.languages matching happens once at config time, aggregates every offender into one error, and never fires for disabled rules.
- **Flat-config composition & verify tail (pass 7)** — `suppression-split-verify-tail`: verify() output NEVER carries `.suppressions`; the splitter replaces (not appends) the last-run slot each verify/verifyAndFix pass, so a directive-suppressed fixable violation is neither fixed nor reported and a clean re-verify resets it to []. `rules-cross-config-merge`: every entry is normalized + structuredClone'd fresh (no aliasing); severity-only second entry splices its severity onto first parent's remaining options; per-key failures rethrow as `Key "<ruleId>": …` with cause; validate() deliberately defers per-rule schema checks to finalize(). `deep-merge-cycle-memo`: `(first, second)` pair memo registered BEFORE recursion terminates cyclic configs; only own-enumerable keys of first participate; explicit undefined in second restores first's value; arrays/primitives overwrite atomically. `eslintrc-key-rejection`: exact trap list env/extends/globals/ignorePatterns/noInlineConfig/overrides/parser/parserOptions/reportUnusedDisableDirectives/root always throw with messageTemplate "eslintrc-incompat"; plugins arrays throw "eslintrc-plugins"; plugins.merge throws on redefine. `source-code-scope-cache`: WeakMap-for-node-keys vs strong name-keyed vars Map vs lazy configNodes — porting all-strong leaks/stales; inner=false ONLY from Program nodes. `cli-options-translation-ladder`: warn rules are filtered from execution only while maxWarnings===-1; quiet fixes use a severity===2 predicate; --config-lookup tri-state algebra. `runtime-info-env-report`: fail-hard environment probes with per-invocation cache; hardcoded dependencies.eslint lookup.

- **ESLint-class instance assembly & cache tail (pass 11)** — `constructor-options-or-url-duality`: the RAW unprocessed options (not processed copies) cross the thread boundary because each worker re-runs processOptions; #optionsOrURL is object on direct construction, URL string after fromOptionsModule overwrite, and only set when concurrency!=="off"; 9-field WeakMap bundle with configs:null lazy slot; suppressions cache prefix "suppressions_"; .eslintignore warning fires at construction on both paths. `results-instance-binding`: foreign results throw ONE typed TypeError (cause preserved) from either loader failure or missing config; "<text>" normalizes to __placeholder__.js BEFORE lookup; unknown rules silently skipped. `net-linting-ratio-concurrency` (refactored): notice TRICHOTOMY selected in lintFiles before spawn — workerCount<=2 ⇒ "disable concurrency", auto ⇒ "…or use a numeric concurrency setting", numeric ⇒ "reduce or disable" (all three arms live-probed); module.exports.calculateWorkerCount consulted through the module object as the stub seam. `result-cache` (refactored): reconcile() is pure delegation with a SINGLE call site at the run tail (after both thread modes, before applySuppressions); setCachedLintResults updates existing found descriptors only — never creates (ghost-file set + reconcile persists nothing); hashOfConfigFor memoized per Config in a module-level WeakMap; workers read the shared cache but all writes funnel through main's instance (read-shared, write-via-main).
- **Warning & default-config planes (pass 14)** — `warning-service-dedup-plane`: one injectable emitter (process.emitWarning default, no-op fallback outside Node) with five typed channels (CircularFixes / EmptyConfig / ESLintIgnore / InactiveFlag_<flag> / PoorConcurrency); worker threads stub exactly emitEmptyConfigWarning + emitInactiveFlagWarning as instance properties because the controlling thread always emits them — dedup by consumer-side muting, never inside the service. `default-config-lazy-proxy`: frozen 4-element defaultConfig whose "@" plugin rules surface is a Proxy forwarding get/has into the LazyLoadingRuleMap (built-ins load only when a config names them; the get-trap shadows Map method names — only ruleId reads and `in` checks work); default ignores node_modules/.git; shared glob entries (js/mjs plain, cjs commonjs+latest) shared BY REFERENCE with defaultRuleTesterConfig, which swaps the plugin entry for `{files:["**"]}` and drops the ignores.
- **ESLint-class orchestration & result tail (pass 12)** — `lintfiles-pattern-collapse-and-tail`: pre-flight collapse/throw/passOnNoPatterns + unlink-swallow + reconcile→suppress→decorate tail order. `fix-types-filter-composition`: two-gate early return, AND-composed predicates, directive pseudo-type, meta.type-less never fixed. `per-file-read-retry-abort`: gate ladder config→cache→read→abort-check→retry with shared-controller abort-on-first-failure. `vertext-placeholder-duality`: swap-in/swap-out config resolution, config-driven block adoption, conditional output/source attachment. `ignored-result-taxonomy`: four-way ignore reason taxonomy + warnIgnored per-call override precedence. `deprecated-rules-lazy-getter`: lazy getter attachment, Config-keyed WeakMap frozen memo, cache-file exclusion. `report-postprocessing-twins`: validate-while-filtering outputFixes + non-mutating error-only getErrorResults projection (fixableErrorCount copied through). `eslint-options-error-accumulation`: fail-all options validation with 13 exact migration hints in one aggregated error.
## Extending the foundation
Add one source-confirmed capsule per new seam: loader line, map entry, decisive source range, invariant, direct-test probe (`tests/lib/**`), and `search_graph` retrieval against project `eslint`.

## Provenance
ESLint MIT at `main@c27bc926e496985eb7911c09eb60914b2e4b5d0f` (`/mnt/hdd/utopia/inspo/eslint`, tag v10.9.0); Codebase Memory project `eslint` — root matches this checkout, head_sha = base_sha = pin, FULL mode, ready, 14,207 nodes / 39,421 edges (verified pass 6; revalidated pass 7, 2026-08-25 — same pin and counts; passes 9–13 re-verified the pin directly against the checkout (HEAD == base == c27bc926e496…, git-clean) with the graph MCP disconnected, using direct source+test reading per AGENTS.md; pass 14 re-verified the pin again (HEAD == tag v10.9.0, porcelain clean) and re-based the last two dc1e7a84-cited engine capsules (autofix-loop, lazy-rule-map-freeze) with re-executed probes — 59 older capsules still cite the old pin in their Source lines pending staged hand-adjudicated rebase, tracked in the work record). History: passes 1–4 pinned `dc1e7a84`; pass 5 mined 10.9.0 drift via a path-slugged twin project that has since been removed from the registry — the twin's claims were re-validated against the fresh short-name graph in pass 6 before any citation. parse_partial limited to docs assets and intentionally-broken fixtures; skipped = 0; generation_matches true. Confirm every claim against source — the graph is an index, not truth.

## Full view (memory graph)
Project `eslint` (short name; root `/mnt/hdd/utopia/inspo/eslint`, head=base=`c27bc92…`, FULL mode, ready — revalidated pass 6 after the pass-5 twin project was retired from the registry) — entry points: `bin/eslint.js` (CLI), `lib/types/index.d.ts loadESLint`, `lib/universal.js`. Packages by node count: rules (2,687), lib (287), linter (257), performance/bench/types/languages/config/rule-tester/shared/services tails. Edge mix: USAGE 16,775 · DEFINES 11,821 · CALLS 5,222 · IMPORTS 1,676 · SIMILAR_TO 131 · TESTS 12. Core seams live in `lib/linter/*` (verify core + code-path-analysis family), `lib/config/*`, `lib/languages/js/**` (SourceCode/TokenStore/Language declaration), `lib/eslint/{eslint,eslint-helpers,worker}.js`, `lib/cli-engine/lint-result-cache.js`, `lib/rule-tester/rule-tester.js`, `lib/rules/utils/*`, `lib/shared/*`, and `lib/services/*`.

## Boundaries
Adopt the verify pipeline, config normalization/caching contracts, discovery/scaling decision, autofix loop, suppression model (both directive and ledger forms), RuleTester self-policing harness, shared AST invariants, and the code-path-analysis kernel; adapt severity vocabularies, schema libraries, storage backends, worker heuristics, and loop/switch grammar coverage to host; omit ESLint's CLI/plugin-ecosystem packaging, docs/website, and the individual ~270 core rules (pass 5 exception: the two drift-fixed rules `no-var`/`no-loss-of-precision` are capsule-mined as fixer-safety/validation-gate patterns). Pass-3 coverage note: every production file under `lib/linter/`, `lib/rules/utils/`, `lib/shared/`, and `lib/services/` is now either capsule-mined or explicitly omitted-with-reason in the work record (`interpolate.js` IS mined via message-interpolation-contract, correcting pass-1's omit ruling; `debug-helpers.js` remains visualization-only). Re-enter on upstream drift past `c27bc92e496985eb7911c09eb60914b2e4b5d0f` or a named porting question — citation-grep FIRST.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`ast-primitives.md`](./ast-primitives.md)
- [`autofix-loop.md`](./autofix-loop.md)
- [`bom-slicing-fix-sweep.md`](./bom-slicing-fix-sweep.md)
- [`char-source-code-units.md`](./char-source-code-units.md)
- [`cli-options-translation-ladder.md`](./cli-options-translation-ladder.md)
- [`config-loader-caching.md`](./config-loader-caching.md)
- [`config-normalization.md`](./config-normalization.md)
- [`config-serialization-processor-binding.md`](./config-serialization-processor-binding.md)
- [`constructor-options-or-url-duality.md`](./constructor-options-or-url-duality.md)
- [`context-prototype-extension.md`](./context-prototype-extension.md)
- [`cpa-analyzer-orchestration.md`](./cpa-analyzer-orchestration.md)
- [`cpa-choice-contexts.md`](./cpa-choice-contexts.md)
- [`cpa-codepath-surface.md`](./cpa-codepath-surface.md)
- [`cpa-fork-context.md`](./cpa-fork-context.md)
- [`cpa-loop-contexts.md`](./cpa-loop-contexts.md)
- [`cpa-segment-lazy-attachment.md`](./cpa-segment-lazy-attachment.md)
- [`cpa-switch-default-rewiring.md`](./cpa-switch-default-rewiring.md)
- [`cpa-try-finally-lanes.md`](./cpa-try-finally-lanes.md)
- [`cycle-aware-dup-detection.md`](./cycle-aware-dup-detection.md)
- [`deep-merge-cycle-memo.md`](./deep-merge-cycle-memo.md)
- [`default-config-lazy-proxy.md`](./default-config-lazy-proxy.md)
- [`default-options-deep-merge.md`](./default-options-deep-merge.md)
- [`deprecated-rules-lazy-getter.md`](./deprecated-rules-lazy-getter.md)
- [`directive-recognition-predicates.md`](./directive-recognition-predicates.md)
- [`disable-directives.md`](./disable-directives.md)
- [`emission-order-conformance.md`](./emission-order-conformance.md)
- [`eslint-options-error-accumulation.md`](./eslint-options-error-accumulation.md)
- [`eslintrc-key-rejection.md`](./eslintrc-key-rejection.md)
- [`feature-flag-ladder.md`](./feature-flag-ladder.md)
- [`file-discovery-workers.md`](./file-discovery-workers.md)
- [`fix-tracker-retained-ranges.md`](./fix-tracker-retained-ranges.md)
- [`fix-types-filter-composition.md`](./fix-types-filter-composition.md)
- [`grapheme-measurement-styling.md`](./grapheme-measurement-styling.md)
- [`id-generator-visitor-primitives.md`](./id-generator-visitor-primitives.md)
- [`ignored-result-taxonomy.md`](./ignored-result-taxonomy.md)
- [`inline-config-comment-gate.md`](./inline-config-comment-gate.md)
- [`inline-config-merge-ladder.md`](./inline-config-merge-ladder.md)
- [`inline-config.md`](./inline-config.md)
- [`js-language-declaration.md`](./js-language-declaration.md)
- [`lazy-rule-map-freeze.md`](./lazy-rule-map-freeze.md)
- [`lintfiles-pattern-collapse-and-tail.md`](./lintfiles-pattern-collapse-and-tail.md)
- [`message-interpolation-contract.md`](./message-interpolation-contract.md)
- [`net-linting-ratio-concurrency.md`](./net-linting-ratio-concurrency.md)
- [`nolop-zero-underflow-gate.md`](./nolop-zero-underflow-gate.md)
- [`novar-hoisted-call-order-guard.md`](./novar-hoisted-call-order-guard.md)
- [`per-file-read-retry-abort.md`](./per-file-read-retry-abort.md)
- [`processor-routing-reconf.md`](./processor-routing-reconf.md)
- [`redundant-inline-config-detection.md`](./redundant-inline-config-detection.md)
- [`report-normalization-pipeline.md`](./report-normalization-pipeline.md)
- [`report-postprocessing-twins.md`](./report-postprocessing-twins.md)
- [`result-cache.md`](./result-cache.md)
- [`results-instance-binding.md`](./results-instance-binding.md)
- [`rule-execution.md`](./rule-execution.md)
- [`rule-fixer-command-factory.md`](./rule-fixer-command-factory.md)
- [`rule-language-compatibility-gate.md`](./rule-language-compatibility-gate.md)
- [`rule-options-pipeline.md`](./rule-options-pipeline.md)
- [`rule-timing-harness.md`](./rule-timing-harness.md)
- [`rules-and-tester.md`](./rules-and-tester.md)
- [`rules-cross-config-merge.md`](./rules-cross-config-merge.md)
- [`runtime-info-env-report.md`](./runtime-info-env-report.md)
- [`schema-shape-resolution-ladder.md`](./schema-shape-resolution-ladder.md)
- [`scoped-naming-grammar.md`](./scoped-naming-grammar.md)
- [`segment-reachability-predicate.md`](./segment-reachability-predicate.md)
- [`selector-parse-specificity.md`](./selector-parse-specificity.md)
- [`severity-stats-normalization.md`](./severity-stats-normalization.md)
- [`shared-traverser-break-semantics.md`](./shared-traverser-break-semantics.md)
- [`source-code-scope-cache.md`](./source-code-scope-cache.md)
- [`source-code-text-loc-lines.md`](./source-code-text-loc-lines.md)
- [`static-string-extraction.md`](./static-string-extraction.md)
- [`suppression-split-verify-tail.md`](./suppression-split-verify-tail.md)
- [`suppressions-ledger.md`](./suppressions-ledger.md)
- [`sync-parse-preprocess-boundary.md`](./sync-parse-preprocess-boundary.md)
- [`test-location-estimator.md`](./test-location-estimator.md)
- [`tester-config-assembly.md`](./tester-config-assembly.md)
- [`tester-runner-shims.md`](./tester-runner-shims.md)
- [`tester-suggestion-ladder.md`](./tester-suggestion-ladder.md)
- [`tester-trap-harness.md`](./tester-trap-harness.md)
- [`timing-merge-display.md`](./timing-merge-display.md)
- [`token-store-cursor-navigation.md`](./token-store-cursor-navigation.md)
- [`token-store-index-map.md`](./token-store-index-map.md)
- [`traversal-instance-caching.md`](./traversal-instance-caching.md)
- [`unicode-flag-probe.md`](./unicode-flag-probe.md)
- [`unused-directive-reporting.md`](./unused-directive-reporting.md)
- [`verify-options-error-attribution.md`](./verify-options-error-attribution.md)
- [`verify-pipeline.md`](./verify-pipeline.md)
- [`vertext-placeholder-duality.md`](./vertext-placeholder-duality.md)
- [`vfile-context-identity.md`](./vfile-context-identity.md)
- [`warning-service-dedup-plane.md`](./warning-service-dedup-plane.md)
- [`worker-cloneability-gate.md`](./worker-cloneability-gate.md)
- [`worker-file-claim-loop.md`](./worker-file-claim-loop.md)
- [`worker-timing-accumulators.md`](./worker-timing-accumulators.md)
