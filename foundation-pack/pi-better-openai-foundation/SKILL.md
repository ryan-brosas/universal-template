---
name: pi-better-openai-foundation
description: "Use when building a pi/OpenAI extension or any realtime-voice/terminal-image agent surface: layered config resolution with clamping, fast-mode payload injection, Codex OAuth credentials, usage polling with generation guards, cross-process floor arbitration for hardware ownership, mode-1004 terminal focus, barge-in echo gating, bounded web fetch, workspace-jailed image inputs, kitty frame animation, and diagnostic secret redaction."
disable-model-invocation: true
---

# pi-better-openai: OpenAI Subscription Extension Foundation

## Use this for
Build a pi coding-agent extension that layers project-over-global JSON config with defaults and numeric clamping, injects a provider-payload field only when a toggle is active for a supported model, resolves OpenAI Codex OAuth credentials, parses/formats subscription usage windows under a generation-guarded polling controller, redacts secrets from diagnostics — plus the pass-2 planes: run a realtime voice session over WebRTC+sideband with cross-process mic-floor arbitration, terminal focus detection via private mode 1004, barge-in echo gating and incremental transcript stitching; fetch the web through a bounded, origin-pinned, size-capped client; validate workspace-jailed image inputs; animate spritesheets in kitty-compatible terminals inside an exact-width footer. The root
`index.ts` composition function (1,359 lines) additionally supplies the extension-wide caching
and event plumbing: a leaf-keyed memo spine for host-store reads, an append-vs-rescan totals
ledger, persist-overlay mirroring of runtime toggle state, an asymmetric status-line packing
ladder, and a session-event invalidation matrix. The live session kernel adds a once-only
failure→terminal latch, single-flight teardown ordering with send-drain-before-close,
race-rechecked startup, a derived audio phase ladder, and an ordered send chain; identity and
path anchors namespace every artifact under one env-overridable agent dir. Source code and direct tests are ground
truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/config-resolution.md` — layer project/global/default config, normalize model keys, clamp numerics, and write config preserving unknown fields.
- `references/fast-mode-injection.md` — inject a provider payload field only when a toggle is active for a supported model, without mutating the original payload.
- `references/codex-auth.md` — resolve Codex OAuth credentials registry-first with auth-file fallback, expiry check, and JWT account-id extraction.
- `references/usage-snapshot.md` — parse and format ChatGPT subscription usage windows (left-percent, reset countdown/clock, Spark scope fallback).
- `references/diagnostic-redaction.md` — strip ANSI/control chars and redact secret-like fields from diagnostic text and structured values.
- `references/live-wire-codec.md` — parse unknown realtime JSON frames into a closed event union without throwing or lying about shape.
- `references/live-context-chunking.md` — split text into UTF-8 byte-budgeted chunks on code-point boundaries without tearing surrogate pairs.
- `references/live-sideband-retry-ladder.md` — retry a flaky WebSocket handshake with settled-latch single-shot promises and abortable exponential backoff.
- `references/live-dual-channel-demux.md` — demux two live transports carrying the same event stream without duplicate delivery.
- `references/live-floor-arbiter.md` — arbitrate exactly one microphone owner across processes with file claims, heartbeats, pid liveness, and asymmetric focus preemption.
- `references/live-focus-reporting.md` — detect terminal focus via DECRQM-probed private mode 1004 with graceful FIFO fallback.
- `references/live-barge-in-gate.md` — gate mic audio against output echo while preserving loud barge-in, with a digital-silence watchdog.
- `references/live-delegation-context.md` — route agent commentary vs held final answers into the voice session to keep one-assistant continuity.
- `references/live-transcript-stitching.md` — merge streaming partial transcripts into deduplicated turn-numbered text with a four-way ladder.
- `references/live-enrollment-lifecycle.md` — separate queue enrollment from session activation so idle windows cost zero open connections.
- `references/live-client-attestation.md` — build a minimal CBOR client-attestation blob by hand with honest error-code fallbacks.
- `references/live-native-bindings.md` — load per-platform native addons through table→validate→init→cache with custom-loader cache bypass.
- `references/live-level-visualizer.md` — animate a level-decay spectrum widget that renders exact-width lines at every terminal width.
- `references/websearch-bounded-fetch.md` — cap response size twice, classify abort-vs-timeout errors, and pin response origin.
- `references/usage-generation-controller.md` — run a periodic refresh loop with generation invalidation and single-flight latest-writer coalescing.
- `references/pets-kitty-animator.md` — animate kitty-protocol images with delete→upload→place choreography and batched cleanup ledgers.
- `references/pets-asset-jail.md` — validate untrusted user image assets with dual realpath containment, symlink refusal, and exact atlas dimensions.
- `references/image-workspace-jail.md` — accept local image paths for upload only after dual containment, content-sniffed formats, and count/byte budgets.
- `references/footer-surface-state-machine.md` — arbitrate full footer / widget / status-line surfaces with latched install flags.
- `references/settings-descriptor-picker.md` — drive a searchable settings UI from descriptors with one write choke point and field-keyed invalidation.
- `references/pets-animation-state-ladder.md` — resolve sprite state precedence across runtime, flash, preview, and configured layers with set-based tool tracking.
- `references/pets-inline-footer-composition.md` — compose animated image lines beside text rows at exact width without breaking cursor state.
- `references/pets-resize-freeze.md` — freeze animation with placeholder rows during resize and defer kitty resets until the terminal settles.
- `references/context-usage-memo-spine.md` — cache expensive host-store reads with leaf+model composite keys and flag+key atomic invalidation.
- `references/footer-totals-dual-ledger.md` — track cumulative token/cost spend O(1) per turn, rebuilding by full rescan whenever history is rewritten.
- `references/persist-overlay-mirroring.md` — mirror runtime toggle state into the cached config unconditionally while gating the disk write behind persistState.
- `references/footer-line-packing-ladder.md` — pack left stats + right model identity into a fixed-width line degrading pad → silent-right-truncate → drop-right → ellipsize-left.
- `references/session-event-matrix.md` — wire every host lifecycle event to memo invalidation, controller mutation, and footer refresh in a fixed order.
- `references/settings-theme-lazy-singleton.md` — defer a host-package dependency out of module evaluation with a memoized dynamic import plus a loud synchronous require-guard.
- `references/live-failure-terminal-latch.md` — latch one terminal failure per session: first error wins, onTerminal fires exactly once, later failures drop silently.
- `references/live-stop-teardown-ordering.md` — tear down recorder → drain queued sends → session.close → transport.close in single-flight order preserving the first cleanup error.
- `references/live-start-race-recheck.md` — start mic capture before negotiation completes while rechecking stopped state after every await to release orphans.
- `references/live-audio-phase-machine.md` — derive UI phase from muted/delegation/output state via a priority ladder with sticky working and dedup/force/safe emission.
- `references/live-send-chain-serialization.md` — serialize ordered protocol sends through a self-healing promise chain with enqueue/run-time stop gates.
- `references/voice-catalog-derived-contract.md` — derive picker values, union type, runtime guard, and typed default from one as-const catalog tuple.
- `references/extension-path-identity-anchors.md` — anchor every artifact under one env-overridable agent dir and namespace config/status/log strings from one identity module.
- `references/live-delegation-message-renderer.md` — render custom-typed delegation messages defensively and key renderer/command/shortcut registration off exported constants.

## Capsule map
- **Config** — `references/config-resolution.md`: `resolveConfig` merge order (defaults → global → project), model-key normalization, per-field numeric clamping, non-destructive `writeConfig`.
- **Fast mode** — `references/fast-mode-injection.md`: `FastController` desired-vs-active split, `injectProviderPayload` non-mutating spread, model allow-list gating.
- **Auth** — `references/codex-auth.md`: `getCodexCredentials` registry-first precedence, `readCodexAuth` OAuth/expiry validation, JWT account-id fallbacks.
- **Usage parsing** — `references/usage-snapshot.md`: `parseUsageSnapshot` bucket normalization, `formatUsageSnapshot` countdown/clock, Spark-scope fallback.
- **Redaction** — `references/diagnostic-redaction.md`: `sanitizeDiagnosticError`/`redactDiagnosticValue`/`maskIdentifier` secret scrubbing.
- **Live wire codec** — `references/live-wire-codec.md`: `parseLiveServerEvent` never-throw closed-union parser with per-field validators and `unknown` wireType catch-all.
- **Live chunking** — `references/live-context-chunking.md`: `chunkLiveContext` UTF-8-byte budget walked by UTF-16 code point, flush-before-overflow.
- **Live retry** — `references/live-sideband-retry-ladder.md`: `#connectSideband` 5×200ms·2ⁿ abort-checked backoff over settled-latch `#openSideband`.
- **Live demux** — `references/live-dual-channel-demux.md`: sideband-open readiness gate forwards normal events from one channel while errors always pass.
- **Live floor** — `references/live-floor-arbiter.md`: `LiveFloorArbiter` wx-create/rename-preempt claims, token read-back confirmation, EPERM-alive pid checks, 8s heartbeat staleness.
- **Live focus** — `references/live-focus-reporting.md`: mode-1004 enable/`CSI I|O`/DECRQM probe tristate parsing with FIFO policy fallback.
- **Barge-in gate** — `references/live-barge-in-gate.md`: echo drop when `outputActive && input < max(0.04, 0.65·output)`, digital-silence watchdog at 32k samples.
- **Delegation context** — `references/live-delegation-context.md`: toolUse→commentary chunks vs settle-time `"Agent Final Message":` framing; id cleared at settle.
- **Transcript stitching** — `references/live-transcript-stitching.md`: growth/re-transmission/append/new-turn ladder + longer-stream-wins finalization.
- **Enrollment lifecycle** — `references/live-enrollment-lifecycle.md`: enroll-park-activate split, deferred-start race recheck, debounced focus edges, OSC 9 unfocused toast.
- **Client attestation** — `references/live-client-attestation.md`: hand-rolled CBOR headers/signal map, error_code 3|4 honesty, darwin-arm64 gate degrading to header-absent.
- **Native bindings** — `references/live-native-bindings.md`: platform package table, four-member structural validation, cause-preserving require wrap, cache bypass for injected loaders.
- **Level visualizer** — `references/live-level-visualizer.md`: 80ms decay loop (`max(input, 0.84·display)`), exact-width render contract, six-field cache, sanitize-before-layout.
- **Websearch fetch** — `references/websearch-bounded-fetch.md`: declared+streamed 256KB gates with body cancel, typed failure precedence, origin pin, http(s)-only citations.
- **Usage controller** — `references/usage-generation-controller.md`: monotonic generation token, in-flight slot with OR-merged queued replay, pre-fetch throttle stamping.
- **Kitty animator** — `references/pets-kitty-animator.md`: per-frame delete→upload→place with ≤4096-chunk RGBA uploads and pending-set cleanup drained once.
- **Asset jail** — `references/pets-asset-jail.md`: resolve+lstat-no-symlink+realpath-pair containment + exact 1536×1872 atlas gate, issue-string diagnostics.
- **Image jail** — `references/image-workspace-jail.md`: lexical+realpath workspace containment, sharp-sniffed formats, 20MB/5-file/50MB budgets before base64 read.
- **Footer surfaces** — `references/footer-surface-state-machine.md`: replace-or-pet escalates to full footer; latched setters keep exactly one owner.
- **Settings picker** — `references/settings-descriptor-picker.md`: descriptor items with live closures; `writeSetting` maps id-prefixes to load-key/render-cache/timer invalidations.
- **Pet states** — `references/pets-animation-state-ladder.md`: preview > flash > runtime > configured-idle precedence; tool concurrency as id set; jittered idle emotes.
- **Inline composition** — `references/pets-inline-footer-composition.md`: exact-width row merge; image lines get blank reservation + cursor-rebalanced deferred sequence.
- **Resize freeze** — `references/pets-resize-freeze.md`: 120ms deadline + placeholder rows + post-freeze kitty reset before first clean re-render.
- **Memo spine** — `references/context-usage-memo-spine.md`: `contextUsage`/`sessionName` leaf+model-keyed memos; invalidate clears flag AND all key slots together.
- **Totals ledger** — `references/footer-totals-dual-ledger.md`: `footerTotals` delta-add on assistant `turn_end`, full `refreshFooterTotals` rescan on compact/tree/non-assistant turns.
- **Persist overlay** — `references/persist-overlay-mirroring.md`: unconditional cached-config overlay of `{active, desiredActive}`, disk read-modify-write only when `persistState`.
- **Line packing** — `references/footer-line-packing-ladder.md`: visibleWidth-measured fit ladder; left never sacrificed while space remains, right truncates silently.
- **Event matrix** — `references/session-event-matrix.md`: event→{invalidate family, mutate controller, updateFooter} table incl. streaming-trio invalidation and poller-before-animator shutdown.
- **Lazy theme singleton** — `references/settings-theme-lazy-singleton.md`: `loadedSettingsListTheme` slot + `??=`-memoized `loadSettingsListTheme` dynamic import + throwing `requireSettingsListTheme` guard; startup never touches the host graph.
- **Failure latch** — `references/live-failure-terminal-latch.md`: `#reportFailure` first-error field + `#emitTerminal` one-shot boolean; failure implies stop; terminal boundary swallows its own errors.
- **Stop ordering** — `references/live-stop-teardown-ordering.md`: memoized `#stopPromise`; flag→recorder→drain `#sendChain`→`session.close`→close; `??=` keeps the first cleanup error; clean stop emits `onTerminal(undefined)` once.
- **Start recheck** — `references/live-start-race-recheck.md`: idempotent `start()`, latched-failure rethrows, capture-before-connect, stopped-recheck after every await with orphan-recorder release.
- **Phase machine** — `references/live-audio-phase-machine.md`: derived ladder muted > working > speaking > listening; working sticky during delegation (`#handleOutputLevel` gate); `#emitPhase` dedup vs force vs `#emitPhaseSafely`.
- **Send chain** — `references/live-send-chain-serialization.md`: self-replacing promise chain, double stop-gates, `.catch` → `#reportFailure` so the chain never rejects; drained before close.
- **Voice catalog** — `references/voice-catalog-derived-contract.md`: one `as const` tuple → values array + indexed union + typed default "sol" + `isLiveVoice`; merge gate drops unknown voices (config.ts:679).
- **Path anchors** — `references/extension-path-identity-anchors.md`: `piAgentDir` PI_CODING_AGENT_DIR override + exact-shape tilde expansion anchoring auth/config/images/queue; CONFIG_BASENAME/STATUS_KEY/logPrefix namespace triple.
- **Delegation renderer** — `references/live-delegation-message-renderer.md`: `messageText` per-item narrowing over unknown content; constant-keyed `registerMessageRenderer`; /live + ctrl+shift+l dual-toggle.

## Extending the foundation
Add one source-confirmed capsule per porting question: loader line, map entry, decisive source, invariant, direct-test probe, and `search_graph` retrieval — then verify loader/map parity (`grep -c '^- \`references/' SKILL.md` == `ls references/*.md | wc -l`).

## Provenance
pi-better-openai (@monotykamary/pi-better-openai, MIT, `main@1188f985389328cff660b6bdbe52f38fdb826c70`, advanced from `86814e9` in pass 4); Codebase Memory project `pi-better-openai` (FULL mode, 1,026 nodes / 3,516 edges after the pass-4 in-place refresh through the live-symlink root — no stale twin; parse_partial ×2 = tests/image.test.ts:20 + tests/websearch.test.ts:12, none cited). Pass 1 (pre-drain) covered config/fast/auth/usage/format (~1.5k LOC); pass 2 (sweep-rover lane) executed a citation-vs-inventory grep exposing all remaining modules and mined them whole-file. All 22 cited paths report `no_recorded_issue` + `metadata_match`. REAL runner: vitest 164/164 GREEN across 17 files in a scratch clone (`npm install` + `env HOME=<clean> npx vitest run`) — the suite is HOME-sensitive: `resolveConfig` merges the developer's real global config at `~/.pi/agent/extensions/pi-better-openai.json`, so run under a clean HOME or one test fails on leaked settings. Pass 3 (deepening-A lane, 2026-08-24, same pin) read the root `index.ts` composition function whole (1,359 lines) and mined its never-cited caching/event seams into 5 more capsule-v2 (28→33); probes re-executed live (`bun install` + clean-HOME vitest 164/164 GREEN at HEAD in a fresh scratch clone). Pass 5 (dedicated lane miner-pi-better-openai, FAC-85, 2026-08-25, same pin re-verified live against checkout HEAD + clean tree) read controller.ts whole (530 lines), reconciled stale bookkeeping (ledger row was pass 0 despite passes 1–4; work record created at inspo/pi-better-openai-work/), and mined 8 uncited seams → capsule-v2 (34→42): failure latch, stop ordering, start race-recheck, phase machine, send chain, voice catalog, path/identity anchors, delegation renderer; all 9 newly cited paths report `no_recorded_issue`/`metadata_match`; vitest runner BLOCKED in-lane this pass (no node_modules in checkout, install forbidden by lane bounds, HOME-sensitive suite) so Gate 5 used deterministic byte-for-byte probes + live graph retrieves incl. adversarial RED miss.

## Full view (memory graph)
Revalidate `pi-better-openai` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. Tests ARE graph-resident at this generation (only `.git` excluded by design). Pass 4 re-pin: 1,026 nodes / 3,516 edges at `main@1188f985` — the pass-4 seam symbols resolve line-exact (`loadSettingsListTheme` :86-91, `requireSettingsListTheme` :92-97), proving the in-place refresh serves post-drift content. Pass 5 re-verified the same generation live (head==base==pin) and all eight pass-5 retrieves resolve line-exact (e.g. `#reportFailure` :513-519, `#stop` :273-303, `#queueSend` :459-467, `piAgentDir` :10-13, `messageText` :78-93).

## Boundaries
Adopt the layered config resolution + clamping, non-mutating provider-payload injection, registry-first credential resolution, usage snapshot parsing/formatting, diagnostic redaction, the whole live-session protocol stack (codec, chunking, floor arbitration, focus reporting, barge-in gating, delegation routing, transcript stitching, enrollment lifecycle), bounded fetch, generation-guarded polling, asset/input jails, kitty animation choreography, the lazy host-dependency singleton for command-time surfaces, and footer/settings machinery. Adapt config basename, supported-model list, service-tier value, endpoints, voice catalog, atlas geometry, and auth paths to the host. Omit Codex product specifics: signaling URLs/headers as contract, ChatGPT search/images request schemas, pet spritesheet assets, and pi ExtensionAPI plumbing unless targeting pi itself.
