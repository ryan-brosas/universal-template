---
name: openreplay-foundation
description: 'Use when porting OpenReplay session-replay mechanics: privacy/sanitization ladders, network request proxies, batch/beacon transport, ingest tokens, assist remote control, or conditional capture. Source-grounded capsule map.'
---

# OpenReplay: Session-Replay Foundation

## Use this for
Use when building or porting session replay, product analytics capture, privacy masking (obscure/hide/private-mode), network request interception proxies, event batching + beacon upload, session token issuance, co-browsing/assist remote control, or conditional ("start when X") recording. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
### Privacy & sanitization
- `references/dom-sanitizer-lattice.md` — Plain/Obscured/Hidden precedence lattice (privateMode > parent > attrs > domSanitizer) with split escalate-only vs recompute write paths.
- `references/string-wiper-input-mask.md` — `SetInputValue` mask-as-length wire semantics and Unicode-whitespace wiper.
- `references/input-privacy-ladder.md` — password→hidden, attribute→obscured, heuristic→plain-gated decision order.
- `references/resanitize-subtree.md` — runtime attribute flips: hidden-boundary rebuild vs leaf re-emit choreography.
- `references/private-mode-redaction.md` — everything-masked default; delete-not-star for network bodies.
- `references/url-param-sanitizer.md` — lowercase allowlist star-masking of jwt/token/password query params.
- `references/img-placeholder-resanitize.md` — natural-size probe → placeholder swap; Firefox SVG carve-out bug to fix.
- `references/network-message-sanitize-order.md` — finalize pipeline order: ignore-filter → token inject → body obscure → URL '******' → user sanitize veto; length-preserving masking.
### Capture core
- `references/ticker-nth-turn.md` — single 30 ms timer multiplexed by skip counters (`t++ >= n` off-by-one).
- `references/time-origin-clock.md` — arithmetic epoch anchor over monotonic clock, re-anchored per session start; signed server-delay correction.
- `references/simple-merge-options.md` — object-only deep merge; arrays/null replace wholesale.
- `references/tracker-start-guards.md` — sentinel/HTTPS/API-checklist/DNT gate order before App creation.
- `references/ws-channel-hook.md` — user websocket capture hook with silent size-bounded drops.
- `references/ngsafe-zone-shims.md` — Zone `__symbol__` lazy lookups bypassing Angular patching.
- `references/idle-callback-scheduler.md` — rAF-chained FIFO replacing requestIdleCallback for commits.
- `references/tracker-network-module-wiring.md` — module-vs-proxy policy split; delete-before-send bodies; failuresOnly gate; iframe re-patch; legacy prototype path.
### Network capture (@openreplay/network-proxy)
- `references/network-proxy-identity-guard.md` — symbol-keyed originals + unwrap-before-wrap so re-patching never stacks proxies.
- `references/xhr-readystate-freeze-map.md` — per-readyState field freeze map; abort-status fallback; token inject gated on readyState===1.
- `references/fetch-clone-chunked-ladder.md` — chunked ⇒ never clone; else clone-once + content-type reader; tee json()/text() without consuming the app's stream.
- `references/beacon-content-type-verdict.md` — synchronous sendBeacon recorded as class-derived Content-Type + boolean 'Sent'/500 verdict.
### Transport & batching
- `references/batch-writer-stream-routing.md` — protocol-v2 routing into player/assets/devtools/analytics builders; fit/flush-retry/one-shot ladder; success-gated index.
- `references/batch-builder-transactional-encode.md` — checkpoint/rewind atomic push; reserve-slot-then-backpatch sizes.
- `references/primitive-encoder-bytes.md` — varint/zigzag/length-prefixed strings with honest boolean overflow returns.
- `references/queue-sender-serial-upload.md` — single-flight send queue, linear backoff, 64 kB keepalive ledger, terminal-stall-on-exhaustion.
- `references/webworker-lifecycle-restart.md` — status-FSM restart guard, visibility-armed 30-min recycle, finalize-before-teardown.
- `references/cold-start-dual-buffer.md` — rotating 30 s pre-consent buffers, throttled commits, empty-tick keepalives.
- `references/offline-recording-roundtrip.md` — localStorage save→restore-once→Timestamp-spliced upload with honest offline clock.
- `references/cross-tab-session-election.md` — BroadcastChannel ask/resp/reg election plus iframe polling queue.
- `references/canvas-frame-packing.md` — u64/u32 framed snapshots, bounded upload queue, pause-on-offscreen.
### Server ingest
- `references/hmac-session-token-codec.md` — base36 body + base58 HMAC-SHA256 stateless token, constant-time compare, 30 s JUST_EXPIRED grace.
- `references/session-start-admission.md` — admission funnel: semver gate (428), dice sampling at new-session only, condition-rate override, one-shot response envelope.
- `references/capture-rate-timestamps.md` — sampling dice + ≤5 min bufferDiff backdate + explicit offline timestamp rule.
- `references/beacon-push-datatype-routing.md` — DataType→Kafka topic router; write-then-401 expiry contract; per-session size cache.
- `references/beacon-cache-ttl.md` — touch-on-read per-session upload caps with background sweeper.
- `references/gzip-body-cap.md` — MaxBytesReader wraps raw body BEFORE gunzip (bomb guard).
- `references/sink-filepool-lru.md` — LRU fd pool, empty-file header rule, batched fsync workers.
### Session identity
- `references/session-token-tab-identity.md` — `token$_$projectKey` storage binding with wipe-on-mismatch; pageNo/tabId persistence; URL stitch format.
### Assist / co-browsing
- `references/assist-identity-gate.md` — handshake identity checks, agent JWT claim-vs-peer binding, presence TTL keys.
- `references/assist-remote-control-fsm.md` — Requesting/Enabled grant machine with per-event id guards.
- `references/webrtc-call-choreography.md` — confirm-before-permission, ICE buffering until answer, ring timeout.
- `references/assist-overlay-canvas.md` — self-hiding annotation/cursor overlays via data-openreplay-hidden.
### Extensibility
- `references/conditions-trigger-latch.md` — message-typed trigger engine with isAny semantics and start latch.
- `references/string-dictionary-attributes.md` — definition-before-reference dict ids for repeated attribute strings.
- `references/tag-watcher-matching.md` — two-tier selector fingerprints + one-shot IntersectionObserver trigger.
- `references/adopted-stylesheets-tracking.md` — descriptor-wrap + 200 ms snapshot diffing of constructed CSS.
- `references/css-inliner-ladder.md` — sheet→fetch→load-event retry; Safari colon & background-clip fixes.
- `references/node-id-packing.md` — 2|7|22-bit level/order/node id bands for cross-domain frames.
- `references/maintainer-node-gc.md` — batched detached-node sweep with window-closed detection.
### Ecosystem (license caveats noted in-capsule)
- `references/analytics-batcher-squash.md` — identity-partitioned people events; increments sum, sets last-wins.
- `references/integration-token-obfuscation.md` — keep-last-4 masked reads; flag-guarded masked writes.
- `references/log-sanitizer.md` — CRLF/control-char strip then truncate for any logged external string.
- `references/ee-connectors-dialect-dispatch.md` — (ee/, license caveat) warehouse dialect switch + worker pool.

## Capsule map
The loader sections above ARE the map: Privacy & sanitization (8) · Capture core (8) · Network capture (4) · Transport & batching (9) · Server ingest (7) · Session identity (1) · Assist (4) · Extensibility (9) · Ecosystem (4) = **54 capsules**, one file each under `references/`.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line above (in its subsystem section) and extend the map count here; keep evidence in the capsule, not this leaf.

## Provenance
OpenReplay monorepo (AGPL-3.0 default; `tracker/` MIT; `networkProxy/` MIT; portions Apache/MIT; `ee/` Enterprise-licensed — patterns only) at `main@99eb60032f70906f6887195c400f173c00a08522` (tag v1.27.0, 2026-08-20). Codebase Memory project `openreplay`: root `/mnt/hdd/utopia/inspo/openreplay`, branch main, FULL mode, 43,930 nodes / 152,728 edges, generation 2026-08-25T20:08:30Z, generation_matches=true, hash_records_complete=true. (Prior generation cited project `ext-openreplay` at a now-nonexistent checkout path; that project is retired — re-pin all retrievals to `openreplay`.) parse_partial limited to SQL migration/Dockerfile/CSS/helm-YAML corpora (none cited). not_indexed = 709 SVG/PNG assets by design. Runner evidence: vitest configured in networkProxy but NOT installed at this checkout (no node_modules); upstream defect at pin — `networkProxy/tests/networkMessage.test.ts:54` self-references `result!.startTime` while `result` is in TDZ (ReferenceError if executed). Jest suite evidence cited inside some capsules (sanitizer/session/BatchBuilder batteries) was executed at this identical HEAD by a predecessor pass and is inherited, not re-executed, in pass 1.

## Full view (memory graph)
Revalidate `openreplay` before porting: run `index_status --verbose`, `check_index_coverage` (stdin JSON), `search_graph` (single positional JSON arg; no `--mode` flag exists), `trace_path`, `get_code_snippet`. Known caveats: BM25 search covers Function/Method nodes well but doc-shaped Section nodes need `search_code`; ee/ Python connector files carry an enterprise-license restriction on code copying (patterns are fair game); `top_observer.ts` ships conflict markers at this pin breaking 2 jest suites; `networkMessage.test.ts` TDZ defect (see Provenance). Source and direct tests decide shipped claims.

## Boundaries
Adopt pure contracts: sanitizer lattices, mask-as-length wire formats, proxy identity guards, clone/chunked response discipline, checkpoint/rewind encoder discipline, keepalive budgeting, token grace windows, consent FSMs. Adapt host-specific integration: storage keys, option names, framework shims, dialect loaders, signaling transports. Omit source-specific product behavior: SaaS endpoints (`api.openreplay.com`), cloud billing, frontend React dashboard, spot extension internals, mobile SDKs, and all `ee/` code beyond pattern reference.
