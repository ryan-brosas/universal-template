<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->

# Continue: Autocomplete & Next-Edit Foundation

## Use this for
Sub-second, trustworthy inline code completion and next-edit prediction: a stage-bail completion pipeline, reuse of in-flight generation across keystrokes, stream-time filtering of model manners, per-model FIM templates with token-budget pruning, prefix-keyed LRU caching, single-line midline-insert handling, and sentinel-token edit prediction — plus the config compilation subsystem that wires models, rules, blocks, and MCP servers into runtime config with a single fatal-error gate. Source and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./autocomplete.md` — the full stage-bail pipeline, generator reuse, stream filters, templating, caching.
- `./llm-abstraction.md` — BaseLLM capability flags, OpenAI-adapter layering, autodetected prompt templates.
- `./next-edit.md` — Instinct/Mercury next-edit prediction: sentinel-token prompting, model-specific providers, diff-based outcomes.
- `./postprocessing.md` — the final safety net: reject degenerate output, model-specific repairs, backtick stripping.
- `./stream-filtering.md` — composable char→line filter pipeline that stops at semantic boundaries.
- `./generator-reuse.md` — keep the in-flight generation alive while the user keeps typing.
- `./lru-cache.md` — prefix-keyed SQLite-persisted LRU cache with longest-match retrieval.
- `./token-pruning.md` — per-model FIM templates that prune to a token budget without cutting the cursor region.
- `./static-context.md` — tree-sitter type-graph analysis that injects relevant type/header snippets.
- `./single-line-completion.md` — diff-pattern classification for midline insertions vs end-of-line.
- `./prefiltering.md` — cheap early bail-outs before any snippet gathering or LLM call.
- `./completion-streamer-transform-split.md` — time-based cancel wraps the raw stream INSIDE reuse; text filters wrap only fresh iterations.
- `./snippet-race-ladder.md` — per-source 100ms races degrade to empty arrays; unraced twin serves offline fidelity.
- `./tokenizer-selection-multiplier.md` — llama-vs-gpt encoding choice plus vendor multiplier inflation before budgeting.
- `./tool-token-arithmetic.md` — constant-table estimates for tools, enum swaps, and chat-message framing.
- `./tool-sequence-history-pruning.md` — non-negotiable-first budgeting with orphan-guarded front-shift pruning.
- `./gitdiff-cache-singleflight.md` — TTL cache joins in-flight fetches and fails open to empty without poisoning.
- `./nextedit-context-mirror.md` — re-running the pipeline up to renderPrompt returns the prefix without a completion.
- `./prev-edit-ledger.md` — 5-entry LRU with session-forget ladder; store-rich (25-line) diffs trimmed downstream.
- `./unified-diff-contract.md` — trailing-newline normalization, display-path fallbacks, structured hunk parsing.
- `./edit-aggregator-clustering.md` — five-trigger cluster lifecycle over per-file batched edit queues with whitespace filtering.
- `./small-edit-fanout.md` — synchronous prompt injection vs fire-and-forget durable-history write.
- `./nextedit-chain-state-machine.md` — singleton chain id + previousCompletions front-consumption; deleteChain re-pushes live file content into history.
- `./nextedit-request-init-bail-ladder.md` — the five silent-undefined exits before any LLM call, in order, plus ignore-list/show-once error funnel.
- `./nextedit-prompt-assembly.md` — [system,user] prompt contract, last-prompt unique-token suffix, prompts[1] fine-tuned dispatch, fence-slice extraction.
- `./nextedit-diff-group-router.md` — myers→bounded groups→cursor-group-now / others-prefetched routing with fresh per-item uuids.
- `./editable-region-sizing-ladder.md` — window margins for partial mode vs token-budget symmetric growth with post-add rollback.
- `./prefetch-queue-lifecycle.md` — two-FIFO chain store; abort→clear→re-arm as one indivisible operation.
- `./nextedit-telemetry-ledger.md` — displayed-then-timeout-rejects default, continuation/500ms-flash cancellation, abort-only-if-displayed.
- `./bracket-matching-stream-filter.md` — complete only pairs you started: accept-state carryover, current-line seed, suffix-front pre-seed, mid-chunk truncation.
- `./char-stream-stop-primitives.md` — hold-back-window stop-token cut, 1.5×-tolerance suffix collision detection, EOL+non-whitespace stop.
- `./multiline-classification-ladder.md` — option → intellisense-forces-multiline → comment veto → language useMultiline hook.
- `./import-definitions-context-plane.md` — focus-triggered LRU of first-100-row import maps feeding cursor-window symbol snippets.
- `./snippet-format-prefix-suffix.md` — comment-wrapped Path-headed snippet blocks (current file last) and selection-spliced prefix construction.
- `./yaml-compile-ladder.md` — pre-read local blocks, override-vs-package unroll fork, one fatal gate after null-stripped validation.
- `./block-unroll-fqsn-templating.md` — parallel `uses:/with:` expansion reassembled by index; inputs→secrets FQSN namespacing; loud missing-input errors.
- `./assistant-merge-dedup.md` — incoming-first, first-seen-wins block merge keyed per type; headers-only requestOptions deep merge.
- `./model-role-defaulting-construction.md` — default chat-esque roles, capability strings that stay undefined for autodetect, AUTODETECT fan-out with loop guard.
- `./tab-autocomplete-model-veto.md` — fatal vs advisory validation taxonomy and the substring veto with coder exemptions.
- `./serialized-config-env-merge.md` — double-parse textual env substitution in JSONC and identity-keyed overlay merging.
- `./selected-models-self-heal.md` — title-match→first-model fallback rectification with apply-role VALID veto and persist-only-on-drift GlobalContext rewrite.
- `./shared-config-salvage-apply.md` — per-field safeParse salvage of security flags plus undefined-gated rename-mapped apply generic over all four config shapes.
- `./browser-config-projection.md` — function-stripping GUI projection with eager configurationStatus freeze and `isLegacy: !!run` legacy markers.
- `./profile-lifecycle-reload-ladder.md` — three-slot cache with pending-promise single-flight, catch-to-ConfigResult never-reject loads, cascade reloads, watch-driven rule-cache chains.
- `./rc-precedence-overlay.md` — fail-open `.continuerc.json` collection and per-file mergeBehavior ladder over the identity-keyed mergeJson kernel.
- `./markdown-rules-source-plane.md` — unshift-assembled rule precedence (colocated cache > .continue markdown > .continuerules), AGENTS>AGENT>CLAUDE priority, invokable→slash-command split, SKILL.md skills loading.
- `./config-handler-cascade-plane.md` — three-level handler cascade (re-election / selection switch / bottom reload) with sticky-fallback profile election and emit-init-on-error handshake.
- `./global-context-disk-store.md` — stateless whole-file read-modify-write JSON store with delete-on-corrupt reads, sharedConfig salvage-and-writeback, and no cross-process locking.
- `./continuerules-dotfile-plane.md` — one raw-text `.continuerules` file per workspace dir, checked-exists-then-read, non-fatal failure, mid-ladder precedence.
- `./markdown-frontmatter-grammar.md` — fail-open `---` frontmatter split (bad YAML degrades to whole-file-as-rule), two-segment file-id naming, dir-scoped default glob anchoring.
- `./tool-definition-gating-matrix.md` — factory-not-const base tool list, flag-gated dependent tools (experimental/recommended-model/remote), duplicate-name non-fatal warning, two-field serialization strip.
- `./mcp-load-injection-tail.md` — four contributions per connected server at load time (tools, prefetched prompts, resource submenu, client-stripped statuses), name-normalization ladder, `mcp://` URI identity.
- `./tool-call-dispatch-error-funnel.md` — never-reject callTool funnel: URI-vs-builtin fork over a 17-case switch, favicon restamp, failure-as-data envelope with typed ContinueError reasons.
- `./mcp-call-result-shaping.md` — MCP wire result mapping: isError throws into the funnel, blob/unknown content degrades to visible error items, dual-key MCP-UI read, fail-soft getResource.
- `./tool-args-parse-coerce.md` — object-shortcut arg parse with `{}` fallback and TWIN deep-parse repair sites (schema coerce before MCP wire calls, inline accessor re-stringify for built-ins).
- `./file-access-policy-ladder.md` — preprocessArgs resolves paths server-side; outside-workspace escalates to permission while disabled stays sticky; unresolved paths fail open to base policy.
- `./terminal-command-policy-veto.md` — in-repo terminal-security classifier: sticky user-disable, rm-rf disables outright, network commands escalate, multi-line most-restrictive fold, parse-fail conservative.
- `./mcp-manager-diff-reconcile.md` — diff-based setConnections: remove-absent/add-missing/in-place option swap, refresh-only-if-changed, generation-swap AbortController, allSettled shutdown.
- `./mcp-connect-state-machine.md` — per-server connect lifecycle: single-flight with forced bypass, cleared-on-connect capability lists, three-way abort race with 20s timeout, capability-gated fail-soft enumeration.
- `./tool-policy-default-taxonomy.md` — four-family permission taxonomy over the 20 built-in definitions plus the user>definition>global resolution ladder with monotone clamping and fail-closed protocol errors.
- `./core-toolcall-protocol-bridge.md` — `tools/call` bridge into callTool: fresh-config dispatch and the throw-vs-data-vs-transparent postures across handleToolCall/preprocessArgs/evaluatePolicy.
- `./mcp-oauth-sse-token-plane.md` — disk-backed per-URL OAuth token store with fail-open reads, sse-only bearer attach at connect time, state-mapped localhost callback that force-refreshes exactly one connection.
- `./stdio-env-path-shell-resolution.md` — whitelist-plus-config env assembly for spawned stdio servers and the login-shell PATH probe adopted only when it differs.
- `./system-message-tool-call-grammar.md` — text-protocol tool calling for models without native tools: hold-back prefix buffer, line-indexed fence parser emitting native-shaped deltas, whole-arg JSON repair, history round-trip.

## Capsule map
- **Pipeline & caching** — `./autocomplete.md`, `./lru-cache.md`, `./prefiltering.md`: stage-bail completion pipeline, prefix-keyed LRU, prefilter gate.
- **Streaming & reuse** — `./stream-filtering.md`, `./generator-reuse.md`: composable filter pipeline, in-flight generation reuse.
- **Prompt & token budget** — `./token-pruning.md`, `./llm-abstraction.md`: per-model templates, token pruning, LLM abstraction.
- **Output safety** — `./postprocessing.md`, `./single-line-completion.md`: reject/repair gate, midline-insert classification.
- **Static & next-edit** — `./static-context.md`, `./next-edit.md`: type-graph contextualization, sentinel-token edit prediction.
- **Snippet gathering & streaming internals** — `./snippet-race-ladder.md`, `./completion-streamer-transform-split.md`, `./gitdiff-cache-singleflight.md`: value-degrading races, cancel-vs-display layer split, TTL single-flight diff cache.
- **Token accounting** — `./tokenizer-selection-multiplier.md`, `./tool-token-arithmetic.md`, `./tool-sequence-history-pruning.md`: encoding choice + vendor inflation, tool/message overhead constants, orphan-safe history pruning.
- **Next-edit context plane** — `./nextedit-context-mirror.md`, `./prev-edit-ledger.md`, `./unified-diff-contract.md`, `./edit-aggregator-clustering.md`, `./small-edit-fanout.md`: offline context mirror, session edit ledger, diff contract, keystroke clustering FSM, dual-consumer fan-out.
- **Next-edit lifecycle plane** — `./nextedit-chain-state-machine.md`, `./nextedit-request-init-bail-ladder.md`, `./nextedit-prompt-assembly.md`, `./nextedit-diff-group-router.md`, `./editable-region-sizing-ladder.md`, `./prefetch-queue-lifecycle.md`, `./nextedit-telemetry-ledger.md`: chain state + teardown re-push, ordered bail ladder, prompt/token contract, cursor-vs-prefetch diff routing, region sizing modes, abort-swap queue lifecycle, accept/reject telemetry ledger.
- **Config compilation plane** — `./yaml-compile-ladder.md`, `./block-unroll-fqsn-templating.md`, `./assistant-merge-dedup.md`: fatal-gated compile ladder, index-preserving unroll kernel, incoming-wins dedup merge.
- **Config model & validation plane** — `./model-role-defaulting-construction.md`, `./tab-autocomplete-model-veto.md`, `./serialized-config-env-merge.md`: role defaulting + AUTODETECT, veto taxonomy, env-substituted serialized configs.
- **Config lifecycle plane** — `./selected-models-self-heal.md`, `./shared-config-salvage-apply.md`, `./browser-config-projection.md`: selection self-heal, org-policy salvage/apply, GUI projection.
- **Reload & source plane** — `./profile-lifecycle-reload-ladder.md`, `./rc-precedence-overlay.md`, `./markdown-rules-source-plane.md`: reload ladders, rc overlays, markdown rule/skill sources.
- **Orchestration & boundary plane** — `./config-handler-cascade-plane.md`, `./global-context-disk-store.md`, `./continuerules-dotfile-plane.md`, `./markdown-frontmatter-grammar.md`, `./tool-definition-gating-matrix.md`, `./mcp-load-injection-tail.md`: handler cascade + election, disk-backed global state, dotfile rule plane, frontmatter grammar, tool gating/serialization, MCP load injection.
- **Autocomplete filter & context internals** — `./bracket-matching-stream-filter.md`, `./char-stream-stop-primitives.md`, `./multiline-classification-ladder.md`, `./import-definitions-context-plane.md`, `./snippet-format-prefix-suffix.md`: bracket-pair ownership across suggestions, char-level stop primitives, multiline decision precedence, focus-warmed import definitions, snippet/prefix formatting.
- **Tool execution & connection plane** — `./tool-call-dispatch-error-funnel.md`, `./mcp-call-result-shaping.md`, `./tool-args-parse-coerce.md`, `./file-access-policy-ladder.md`, `./terminal-command-policy-veto.md`, `./mcp-manager-diff-reconcile.md`, `./mcp-connect-state-machine.md`: error-funnel dispatch, wire-result degradation, twin arg-repair sites, path-driven policy escalation, terminal command veto, diff-based connection reconcile, connect state machine.
- **Policy resolution ring & transport boundary plane** — `./tool-policy-default-taxonomy.md`, `./core-toolcall-protocol-bridge.md`, `./mcp-oauth-sse-token-plane.md`, `./stdio-env-path-shell-resolution.md`, `./system-message-tool-call-grammar.md`: default taxonomy + clamp ladder, protocol-bridge throw/data postures, OAuth token loop, login-shell PATH env, fence grammar for non-native-tool models.

## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
Continue (Apache-2.0), `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory project `continue` (51,815 nodes / 120,775 edges, full mode; HEAD==base_sha==`5522c6f4` re-verified at pass 3 with origin/main fetched = 0 behind — zero drift; registered root `/mnt/hdd/utopia/inspo/continue` is a LIVE SYMLINK into `inspo/coding-agents/continue`, graphs serve real bytes — benign-twin class, no adoption needed; 42 parse-partial files are gui/sync noise, none cited by pass 3; 315 by-design not-indexed assets). Passes: 1 (2026-08-23 legacy sweep), 2 (2026-08-23: snippet/generation planes + countTokens + nextEdit/context), 3 (2026-08-24: citation-vs-inventory over core/autocomplete+core/nextEdit exposed 28 never-cited files → +12 capsules on the NextEdit lifecycle plane and autocomplete filter/context internals), 4 (2026-08-25: config compilation plane — clusters 69+109 were never cited → +6 capsules over core/config/{yaml,load,validation,profile} + packages/config-yaml unroll/merge/dedup kernel; graph re-verified heads/main@5522c6f44ca0 == git HEAD, 51,815 nodes / 120,775 edges, generation_matches true; runner block recorded: vitest configured but node_modules absent repo-wide, deterministic evidence used), 5 (2026-08-25: config lifecycle plane — +6 capsules over selectedModels self-heal, sharedConfig salvage/four-shape apply, finalToBrowserConfig projection, ProfileLifecycleManager/LocalProfileLoader/ConfigHandler reload ladder, json/loadRcConfigs+util/merge rc overlays, markdown rules/skills source plane with CodebaseRulesCache ordering; graph re-verified heads/main@5522c6f44ca0 == git HEAD, 51,815 nodes / 120,775 edges, all 14 cited paths no_recorded_issue / generation_matches true; runner block still open), 6 (2026-08-25: orchestration & boundary plane — +6 capsules closing all pass-5 targets: ConfigHandler whole-file cascade (election stickiness, emit-init-on-error), GlobalContext stateless disk store with salvage ladder, .continuerules dotfile plane, markdownToRule fail-open frontmatter grammar, tool gating matrix + serializeTool strip, MCP load-injection tail with name normalization and mcp:// identity; graph re-verified heads/main@5522c6f44ca0 == git HEAD, 51,815 nodes / 120,775 edges, all 7 cited paths no_recorded_issue / generation_matches true; direct tests read: toolDefinitions.test.ts, searchWebGating.vitest.ts, mcpToolName.vitest.ts; runner block still open — deterministic Gate-5 evidence used).

Pass 7–9 provenance correction and completion (2026-08-26): an earlier record claimed pass 7 landed seven capsules with full wiring (59 refs) — disk truth found at pass 9 was 57 refs wired only through pass 6 (52 loaders), five pass-7-content capsules present but UNWIRED under different filenames, two pass-7 capsules missing, and all pass-8 production lost (learning note survived). This leaf now carries the reconciled truth: 64 capsule-v2 references. Pass 9 re-derived every seam's evidence chain fresh (search_graph rank-1 hits, trace_path incl. recorded callers_total-0 gaps for setConnections/connectClient/getEnvPathFromUserShell vs direct-read drivers, get_code_snippet byte-matches, check_index_coverage no_recorded_issue across 20 cited paths @ gen 2026-08-16T00:20:33Z; HEAD==base==`5522c6f4` == pin, porcelain empty pre/post), adjudicated all five orphan capsules source-correct (two Probe/caveat repairs: parseArgs.vitest.ts :379–447 exists; packages/terminal-security is IN-repo, graph-indexed, 1241L), authored the two missing pass-7 capsules and five pass-8 capsules, and wired everything in one bounded change. NEW direct-test evidence captured this pass: core/context/mcp/MCPConnection.vitest.ts (460L — invalid-type-in-connectClient, already-connected short-circuit, ENOENT enrichment, WSL/cmd.exe matrix, shellPath mock seam), MCPOauth.vitest.ts (300L), MCPManagerSingleton.vitest.ts (195L), requestRule.test.ts (239L), parseSystemToolCall.vitest.ts (281L) + toolCodeblocks/interceptSystemToolCalls.vitest.ts (423L).

## Full view (memory graph)
Revalidate `continue` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Passes 7–9 additions: adopt failure-as-data tool envelopes (only dispatch-time unknowns throw; policy evaluation of unknown tools returns base unchanged while preprocessing throws), monotone-only policy refinement enforced twice (GUI clamp + server veto), diff-based connection reconcile keyed by transport equality with in-place cosmetic swaps, cleared-on-connect capability lists, sse-only OAuth attach that mutates options in place (safe ONLY because remote reconcile compares urls), whitelist-plus-login-shell PATH assembly for spawned servers, and hold-back-buffer fence parsing that emits native-shaped deltas for non-tool models; treat the case-0→case-1 fall-through in handleToolCallBuffer as load-bearing, `codeVerifier()`'s ""-not-undefined return as API surface, and the blob double-push quirk in MCP result shaping as a known latent bug to fix on port, not copy.

Passes 5–6 additions: adopt write-then-reload pairing for global-state mutations, the emit-init-on-error startup handshake, sticky-fallback profile-election persistence, factory-not-const registries rebuilt on every reload, fail-open rule-text parsing (bad frontmatter degrades to whole-file-as-rule), and client-stripped serialization that removes exactly the execution-machinery fields; treat `{...config}` shallow copies inside selection rectification as input-mutation traps, remember `mergeJson` recursion drops mergeKeys (identity functions apply only at top level), and treat GlobalContext's lock-free whole-file writes as last-writer-wins — do not port where multi-writer consistency matters.

Cumulative contract: Adopt the stage-bail pipeline, generator reuse, stream-filter, token-pruning, LRU-cache, postprocess-gate, and next-edit contracts; adapt model providers and editor transports; omit Continue-specific IDE integrations, onboarding, and the dormant `IS_NEXT_EDIT_ACTIVE` flag unless a target requires them. Pass-2 additions: adopt value-degrading races, cancel-vs-display stream layering, tokenizer multipliers, tool-token constants, orphan-safe pruning; treat `processNextEditData`'s hardcoded Codestral/token-budget experiment scaffolding and the `(as any).latestContextData` cast as residue NOT to copy. Pass-3 additions: adopt the chain front-consumption rule and deleteChain history re-push, ordered bail ladder with capability-gate-before-file-work, prompts[1] fine-tuned dispatch, cursor-vs-prefetch diff routing, abort→clear→re-arm queue lifecycle, timeout-reject telemetry defaults, bracket-ownership carryover, hold-back-window stop-token filtering, and focus-warmed import definitions; treat the commented-out midline heuristic in `shouldCompleteMultiline` as deliberately disabled (do not "fix"), the dormant `provideInlineCompletionItemsWithChain` wrapper as kept-by-choice, and PrefetchQueue's `peekThreeProcessed`/`setPreetchLimit` console-debug helpers as scaffolding NOT to port. Pass-4 additions: adopt the single-fatal-gate compile ladder, index-preserving parallel unroll, incoming-first dedup with explicit per-type identity keys, undefined-when-absent capability flags, per-key env application, and textual env substitution; treat the JSON config plane as the legacy path kept for backward compatibility (do not extend it), and keep heuristic vetoes (mistral/instruct with deepseek/codestral/coder exemptions) as editable data. Latent trap: `createDiff` returns `""` for TokenLineDiff/RawBeforeAfter (dead slots), and consumers strip 4 header lines from stored unidiffs — changing either silently breaks the other. Second latent trap (pass 4): `intermediateToFinalConfig`'s applyCo... (line truncated to 2000 chars)

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`assistant-merge-dedup.md`](./assistant-merge-dedup.md)
- [`autocomplete.md`](./autocomplete.md)
- [`block-unroll-fqsn-templating.md`](./block-unroll-fqsn-templating.md)
- [`bracket-matching-stream-filter.md`](./bracket-matching-stream-filter.md)
- [`browser-config-projection.md`](./browser-config-projection.md)
- [`char-stream-stop-primitives.md`](./char-stream-stop-primitives.md)
- [`completion-streamer-transform-split.md`](./completion-streamer-transform-split.md)
- [`config-handler-cascade-plane.md`](./config-handler-cascade-plane.md)
- [`continuerules-dotfile-plane.md`](./continuerules-dotfile-plane.md)
- [`core-toolcall-protocol-bridge.md`](./core-toolcall-protocol-bridge.md)
- [`edit-aggregator-clustering.md`](./edit-aggregator-clustering.md)
- [`editable-region-sizing-ladder.md`](./editable-region-sizing-ladder.md)
- [`file-access-policy-ladder.md`](./file-access-policy-ladder.md)
- [`generator-reuse.md`](./generator-reuse.md)
- [`gitdiff-cache-singleflight.md`](./gitdiff-cache-singleflight.md)
- [`global-context-disk-store.md`](./global-context-disk-store.md)
- [`import-definitions-context-plane.md`](./import-definitions-context-plane.md)
- [`llm-abstraction.md`](./llm-abstraction.md)
- [`lru-cache.md`](./lru-cache.md)
- [`markdown-frontmatter-grammar.md`](./markdown-frontmatter-grammar.md)
- [`markdown-rules-source-plane.md`](./markdown-rules-source-plane.md)
- [`mcp-call-result-shaping.md`](./mcp-call-result-shaping.md)
- [`mcp-connect-state-machine.md`](./mcp-connect-state-machine.md)
- [`mcp-load-injection-tail.md`](./mcp-load-injection-tail.md)
- [`mcp-manager-diff-reconcile.md`](./mcp-manager-diff-reconcile.md)
- [`mcp-oauth-sse-token-plane.md`](./mcp-oauth-sse-token-plane.md)
- [`model-role-defaulting-construction.md`](./model-role-defaulting-construction.md)
- [`multiline-classification-ladder.md`](./multiline-classification-ladder.md)
- [`next-edit.md`](./next-edit.md)
- [`nextedit-chain-state-machine.md`](./nextedit-chain-state-machine.md)
- [`nextedit-context-mirror.md`](./nextedit-context-mirror.md)
- [`nextedit-diff-group-router.md`](./nextedit-diff-group-router.md)
- [`nextedit-prompt-assembly.md`](./nextedit-prompt-assembly.md)
- [`nextedit-request-init-bail-ladder.md`](./nextedit-request-init-bail-ladder.md)
- [`nextedit-telemetry-ledger.md`](./nextedit-telemetry-ledger.md)
- [`postprocessing.md`](./postprocessing.md)
- [`prefetch-queue-lifecycle.md`](./prefetch-queue-lifecycle.md)
- [`prefiltering.md`](./prefiltering.md)
- [`prev-edit-ledger.md`](./prev-edit-ledger.md)
- [`profile-lifecycle-reload-ladder.md`](./profile-lifecycle-reload-ladder.md)
- [`rc-precedence-overlay.md`](./rc-precedence-overlay.md)
- [`selected-models-self-heal.md`](./selected-models-self-heal.md)
- [`serialized-config-env-merge.md`](./serialized-config-env-merge.md)
- [`shared-config-salvage-apply.md`](./shared-config-salvage-apply.md)
- [`single-line-completion.md`](./single-line-completion.md)
- [`small-edit-fanout.md`](./small-edit-fanout.md)
- [`snippet-format-prefix-suffix.md`](./snippet-format-prefix-suffix.md)
- [`snippet-race-ladder.md`](./snippet-race-ladder.md)
- [`static-context.md`](./static-context.md)
- [`stdio-env-path-shell-resolution.md`](./stdio-env-path-shell-resolution.md)
- [`stream-filtering.md`](./stream-filtering.md)
- [`system-message-tool-call-grammar.md`](./system-message-tool-call-grammar.md)
- [`tab-autocomplete-model-veto.md`](./tab-autocomplete-model-veto.md)
- [`terminal-command-policy-veto.md`](./terminal-command-policy-veto.md)
- [`token-pruning.md`](./token-pruning.md)
- [`tokenizer-selection-multiplier.md`](./tokenizer-selection-multiplier.md)
- [`tool-args-parse-coerce.md`](./tool-args-parse-coerce.md)
- [`tool-call-dispatch-error-funnel.md`](./tool-call-dispatch-error-funnel.md)
- [`tool-definition-gating-matrix.md`](./tool-definition-gating-matrix.md)
- [`tool-policy-default-taxonomy.md`](./tool-policy-default-taxonomy.md)
- [`tool-sequence-history-pruning.md`](./tool-sequence-history-pruning.md)
- [`tool-token-arithmetic.md`](./tool-token-arithmetic.md)
- [`unified-diff-contract.md`](./unified-diff-contract.md)
- [`yaml-compile-ladder.md`](./yaml-compile-ladder.md)
