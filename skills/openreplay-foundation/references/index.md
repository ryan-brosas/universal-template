<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->


# OpenReplay: Session-Replay Foundation

## Use this for
Use when building or porting session replay, product analytics capture, privacy masking (obscure/hide/private-mode), network request interception proxies, event batching + beacon upload, session token issuance, co-browsing/assist remote control, or conditional ("start when X") recording. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
### Privacy & sanitization
- `./dom-sanitizer-lattice.md` — Plain/Obscured/Hidden precedence lattice (privateMode > parent > attrs > domSanitizer) with split escalate-only vs recompute write paths.
- `./string-wiper-input-mask.md` — `SetInputValue` mask-as-length wire semantics and Unicode-whitespace wiper.
- `./input-privacy-ladder.md` — password→hidden, attribute→obscured, heuristic→plain-gated decision order.
- `./resanitize-subtree.md` — runtime attribute flips: hidden-boundary rebuild vs leaf re-emit choreography.
- `./private-mode-redaction.md` — everything-masked default; delete-not-star for network bodies.
- `./url-param-sanitizer.md` — lowercase allowlist star-masking of jwt/token/password query params.
- `./img-placeholder-resanitize.md` — natural-size probe → placeholder swap; Firefox SVG carve-out bug to fix.
- `./network-message-sanitize-order.md` — finalize pipeline order: ignore-filter → token inject → body obscure → URL '******' → user sanitize veto; length-preserving masking.
### Capture core
- `./ticker-nth-turn.md` — single 30 ms timer multiplexed by skip counters (`t++ >= n` off-by-one).
- `./time-origin-clock.md` — arithmetic epoch anchor over monotonic clock, re-anchored per session start; signed server-delay correction.
- `./simple-merge-options.md` — object-only deep merge; arrays/null replace wholesale.
- `./tracker-start-guards.md` — sentinel/HTTPS/API-checklist/DNT gate order before App creation.
- `./ws-channel-hook.md` — user websocket capture hook with silent size-bounded drops.
- `./ngsafe-zone-shims.md` — Zone `__symbol__` lazy lookups bypassing Angular patching.
- `./idle-callback-scheduler.md` — rAF-chained FIFO replacing requestIdleCallback for commits.
- `./tracker-network-module-wiring.md` — module-vs-proxy policy split; delete-before-send bodies; failuresOnly gate; iframe re-patch; legacy prototype path.
### Network capture (@openreplay/network-proxy)
- `./network-proxy-identity-guard.md` — symbol-keyed originals + unwrap-before-wrap so re-patching never stacks proxies.
- `./xhr-readystate-freeze-map.md` — per-readyState field freeze map; abort-status fallback; token inject gated on readyState===1.
- `./fetch-clone-chunked-ladder.md` — chunked ⇒ never clone; else clone-once + content-type reader; tee json()/text() without consuming the app's stream.
- `./beacon-content-type-verdict.md` — synchronous sendBeacon recorded as class-derived Content-Type + boolean 'Sent'/500 verdict.
### Transport & batching
- `./batch-writer-stream-routing.md` — protocol-v2 routing into player/assets/devtools/analytics builders; fit/flush-retry/one-shot ladder; success-gated index.
- `./batch-builder-transactional-encode.md` — checkpoint/rewind atomic push; reserve-slot-then-backpatch sizes.
- `./primitive-encoder-bytes.md` — varint/zigzag/length-prefixed strings with honest boolean overflow returns.
- `./queue-sender-serial-upload.md` — single-flight send queue, linear backoff, 64 kB keepalive ledger, terminal-stall-on-exhaustion.
- `./webworker-lifecycle-restart.md` — status-FSM restart guard, visibility-armed 30-min recycle, finalize-before-teardown.
- `./cold-start-dual-buffer.md` — rotating 30 s pre-consent buffers, throttled commits, empty-tick keepalives.
- `./offline-recording-roundtrip.md` — localStorage save→restore-once→Timestamp-spliced upload with honest offline clock.
- `./cross-tab-session-election.md` — BroadcastChannel ask/resp/reg election plus iframe polling queue.
- `./canvas-frame-packing.md` — u64/u32 framed snapshots, bounded upload queue, pause-on-offscreen.
### Server ingest
- `./hmac-session-token-codec.md` — base36 body + base58 HMAC-SHA256 stateless token, constant-time compare, 30 s JUST_EXPIRED grace.
- `./session-start-admission.md` — admission funnel: semver gate (428), dice sampling at new-session only, condition-rate override, one-shot response envelope.
- `./capture-rate-timestamps.md` — sampling dice + ≤5 min bufferDiff backdate + explicit offline timestamp rule.
- `./beacon-push-datatype-routing.md` — DataType→Kafka topic router; write-then-401 expiry contract; per-session size cache.
- `./beacon-cache-ttl.md` — touch-on-read per-session upload caps with background sweeper.
- `./gzip-body-cap.md` — MaxBytesReader wraps raw body BEFORE gunzip (bomb guard).
- `./sink-filepool-lru.md` — LRU fd pool, empty-file header rule, batched fsync workers.
### Session identity
- `./session-token-tab-identity.md` — `token$_$projectKey` storage binding with wipe-on-mismatch; pageNo/tabId persistence; URL stitch format.
### Assist / co-browsing
- `./assist-identity-gate.md` — handshake identity checks, agent JWT claim-vs-peer binding, presence TTL keys.
- `./assist-remote-control-fsm.md` — Requesting/Enabled grant machine with per-event id guards.
- `./webrtc-call-choreography.md` — confirm-before-permission, ICE buffering until answer, ring timeout.
- `./assist-overlay-canvas.md` — self-hiding annotation/cursor overlays via data-openreplay-hidden.
### Extensibility
- `./conditions-trigger-latch.md` — message-typed trigger engine with isAny semantics and start latch.
- `./string-dictionary-attributes.md` — definition-before-reference dict ids for repeated attribute strings.
- `./tag-watcher-matching.md` — two-tier selector fingerprints + one-shot IntersectionObserver trigger.
- `./adopted-stylesheets-tracking.md` — descriptor-wrap + 200 ms snapshot diffing of constructed CSS.
- `./css-inliner-ladder.md` — sheet→fetch→load-event retry; Safari colon & background-clip fixes.
- `./node-id-packing.md` — 2|7|22-bit level/order/node id bands for cross-domain frames.
- `./maintainer-node-gc.md` — batched detached-node sweep with window-closed detection.
### Ecosystem (license caveats noted in-capsule)
- `./analytics-batcher-squash.md` — identity-partitioned people events; increments sum, sets last-wins.
- `./integration-token-obfuscation.md` — keep-last-4 masked reads; flag-guarded masked writes.
- `./log-sanitizer.md` — CRLF/control-char strip then truncate for any logged external string.
- `./ee-connectors-dialect-dispatch.md` — (ee/, license caveat) warehouse dialect switch + worker pool.
- `./app-start-deferral-gate.md` — how do you make session `start()` idempotent, election-aware, and deferred until the tab is visible.
- `./commit-recovery-ladder.md` — how does a ~30 ms commit loop survive a dead worker and an idle session.
- `./console-proxy-capture.md` — how do you record console output with format-string expansion and rate limits.
- `./exception-normalization.md` — how are Error objects, string throws, and promise rejections normalized into one message.
- `./main-thread-gzip-offload.md` — where does compression happen when the worker can't or shouldn't gzip a batch.
- `./start-response-client-contract.md` — what must the browser do with `/v1/web/start`'s response before recording may begin.

## Capsule map
The loader sections above ARE the map: Privacy & sanitization (8) · Capture core (8) · Network capture (4) · Transport & batching (9) · Server ingest (7) · Session identity (1) · Assist (4) · Extensibility (9) · Ecosystem (4) = **54 capsules**, one file each under `./`.
- **Adopted stylesheets + CSS rules tracking** — `adopted-stylesheets-tracking`: how do constructed CSSStyleSheet changes get recorded across Document and ShadowRoots.
- **Analytics Batcher people-event squashing** — `analytics-batcher-squash`: how do identify/increment events dedupe before hitting the wire.
- **Assist identity gate + JWT authorizer** — `assist-identity-gate`: how does the socket server refuse unknown peers and bind agents to rooms.
- **AnnotationCanvas + agent Mouse overlay** — `assist-overlay-canvas`: how do you draw on the user's screen and render a remote cursor that the tracker itself hides.
- **Assist remote-control consent FSM** — `assist-remote-control-fsm`: what state machine gates agent mouse/keyboard injection.
- **BatchBuilder transactional encode** — `batch-builder-transactional-encode`: how does a fixed-size encoder accept or reject a whole message atomically without corrupting prior bytes.
- **BatchWriter stream routing & soft-budget ladder** — `batch-writer-stream-routing`: how do four parallel batch streams share one message firehose without a single oversized message wedging the session.
- **BeaconCache TTL refresh** — `beacon-cache-ttl`: how is the per-session upload cap stored so hot sessions stay hot.
- **Beacon content-type verdict** — `beacon-content-type-verdict`: how do you record a fire-and-forget sendBeacon whose only outcome signal is a boolean.
- **Beacon push handler & DataType routing** — `beacon-push-datatype-routing`: how does one ingest endpoint accept compressed multi-stream batches and route them to the right Kafka topics without dropping expired-token data.
- **Canvas frame packing + upload queue** — `canvas-frame-packing`: how are periodic canvas snapshots batched, capped, and shipped.
- **Capture-rate sampling dice + offline timestamp rule** — `capture-rate-timestamps`: how does the server decide a session is recorded and when its clock starts.
- **Cold-start dual-buffer buffering** — `cold-start-dual-buffer`: how do you record before consent and replay the buffer when (and only when) start() arrives.
- **ConditionsManager trigger-once** — `conditions-trigger-latch`: how does "start recording when X happens" evaluate without double starts.
- **RickRoll cross-tab BroadcastChannel election** — `cross-tab-session-election`: how do same-origin tabs agree on ONE active session.
- **CSS inliner fallback ladder** — `css-inliner-ladder`: how do cross-origin stylesheets get captured when direct sheet access throws.
- **DOM sanitizer level lattice** — `dom-sanitizer-lattice`: how do you mask/obscure/hide recorded DOM content with parent-inherited, attribute-driven, and privacy-mode levels that can also be LOWERED at runtime.
- **EE connectors worker pool + dialect dispatch** — `ee-connectors-dialect-dispatch`: how do decoded session messages fan out to five warehouse SQL dialects.
- **Fetch clone/chunked ladder** — `fetch-clone-chunked-ladder`: when may you `resp.clone()` to read a response body, and how do you tee json()/text() without consuming the app's stream.
- **Gzip beacon body reader with per-session cap** — `gzip-body-cap`: how is a tracker upload body size-bounded and transparently decompressed.
- **HMAC session token codec (Go)** — `hmac-session-token-codec`: how do you mint stateless, expiring, self-contained session tokens without JWT overhead.
- **requestIdleCb FIFO scheduler** — `idle-callback-scheduler`: why replace requestIdleCallback with a rAF-chained queue.
- **Image placeholder + resanitize hook** — `img-placeholder-resanitize`: how are hidden/broken images replaced without breaking layout.
- **Input default-obscured ladder** — `input-privacy-ladder`: which heuristic decides a field is sensitive when no attribute exists.
- **Issue-tracking integration token obfuscation** — `integration-token-obfuscation`: how are Jira/GitHub tokens displayed and updated without round-tripping secrets.
- **Log-forging sanitizer (API side)** — `log-sanitizer`: how are externally-sourced strings made safe before log interpolation.
- **Maintainer detached-node GC** — `maintainer-node-gc`: how are leaked node registrations from removed iframes/windows reclaimed.
- **Network message sanitize order** — `network-message-sanitize-order`: in what order must header filtering, body obscuring, URL masking, and user sanitize run when finalizing a recorded request.
- **Network-proxy identity guard** — `network-proxy-identity-guard`: how do you patch fetch/XHR/sendBeacon without ever stacking a proxy on a proxy.
- **ngSafe (Angular Zone.js) browser-method shims** — `ngsafe-zone-shims`: why do MutationObserver/addEventListener need Zone-aware wrappers.
- **Node id packing (level/order/node 22-bit)** — `node-id-packing`: how are cross-domain iframe node ids allocated without collisions.
- **Offline recording buffer round-trip** — `offline-recording-roundtrip`: how do you record with no network, persist to localStorage, and upload later with an honest time origin.
- **PrimitiveEncoder byte primitives** — `primitive-encoder-bytes`: how do you encode varints, zigzag ints, and length-prefixed strings into a fixed Uint8Array with honest overflow returns.
- **privateMode global redaction** — `private-mode-redaction`: what does "mask everything by default" actually rewrite, field by field.
- **QueueSender serial send queue** — `queue-sender-serial-upload`: how does a WebWorker deliver batches over flaky fetch with bounded retries, keepalive budgeting, and a single-file queue.
- **resanitize two-way re-emit** — `resanitize-subtree`: how do you change masking AFTER recording started without corrupting the player DOM.
- **Session-start admission & sampling** — `session-start-admission`: how does the ingest edge decide who gets recorded, and what exactly rides back to the tracker.
- **Session token & tab identity** — `session-token-tab-identity`: how do you resume a recording session across tabs/reloads while keeping per-tab isolation and project binding.
- **simpleMerge deep option merge** — `simple-merge-options`: how do user options merge with nested defaults without array clobbering surprises.
- **Sink FilePool LRU + size cap** — `sink-filepool-lru`: how do you write thousands of concurrent session files without exhausting FDs.
- **AttributeSender StringDictionary** — `string-dictionary-attributes`: when do you dictionary-encode attribute names/values on the wire.
- **stringWiper + input masking wire format** — `string-wiper-input-mask`: why is the recorded value empty with a numeric mask.
- **TagWatcher two-tier matching + IntersectionObserver trigger** — `tag-watcher-matching`: how do server-defined element tags fire exactly once on render.
- **Ticker n-th turn scheduler** — `ticker-nth-turn`: how do 30 ms capture cycles share one timer without starving.
- **Time-origin clock discipline** — `time-origin-clock`: how do you build session timestamps from a monotonic clock that still agree with the server's wall clock.
- **Tracker network-module wiring** — `tracker-network-module-wiring`: how does one capture module serve proxy and legacy transports, iframes, privateMode, failuresOnly, and axios at once.
- **Tracker singleton + start guards** — `tracker-start-guards`: what one-instance and environment checks gate `start()`.
- **URL query-param sanitizer** — `url-param-sanitizer`: which default params are masked in page locations and how does hash-router rewriting interact.
- **WebRTC call offer/answer with buffered ICE** — `webrtc-call-choreography`: how does an inbound agent call get user consent without losing candidates.
- **Webworker lifecycle & hidden-tab restart** — `webworker-lifecycle-restart`: how does a message worker self-heal from dead senders, auth loss, and 30-minute hidden tabs.
- **WSChannel custom-event hook** — `ws-channel-hook`: how is arbitrary websocket traffic recorded with bounded payload sizes.
- **XHR readyState freeze map** — `xhr-readystate-freeze-map`: which request fields may be written at which readyState, and how does an abort keep its status.
- **App start-deferral gate** — `app-start-deferral-gate`: how do you make session `start()` idempotent, election-aware, and deferred until the tab is visible.
- **Commit-failure recovery ladder** — `commit-recovery-ladder`: how does a ~30 ms commit loop survive a dead worker and an idle session.
- **Console capture via Proxy + throttling** — `console-proxy-capture`: how do you record console output with format-string expansion and rate limits.
- **Exception capture ladder** — `exception-normalization`: how are Error objects, string throws, and promise rejections normalized into one message.
- **Main-thread gzip offload** — `main-thread-gzip-offload`: where does compression happen when the worker can't or shouldn't gzip a batch.
- **Start-response client contract** — `start-response-client-contract`: what must the browser do with `/v1/web/start`'s response before recording may begin.
## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line above (in its subsystem section) and extend the map count here; keep evidence in the capsule, not this leaf.

## Provenance
OpenReplay monorepo (AGPL-3.0 default; `tracker/` MIT; `networkProxy/` MIT; portions Apache/MIT; `ee/` Enterprise-licensed — patterns only) at `main@99eb60032f70906f6887195c400f173c00a08522` (tag v1.27.0, 2026-08-20). Codebase Memory project `openreplay`: root `/mnt/hdd/utopia/inspo/openreplay`, branch main, FULL mode, 43,930 nodes / 152,728 edges, generation 2026-08-25T20:08:30Z, generation_matches=true, hash_records_complete=true. (Prior generation cited project `ext-openreplay` at a now-nonexistent checkout path; that project is retired — re-pin all retrievals to `openreplay`.) parse_partial limited to SQL migration/Dockerfile/CSS/helm-YAML corpora (none cited). not_indexed = 709 SVG/PNG assets by design. Runner evidence: vitest configured in networkProxy but NOT installed at this checkout (no node_modules); upstream defect at pin — `networkProxy/tests/networkMessage.test.ts:54` self-references `result!.startTime` while `result` is in TDZ (ReferenceError if executed). Jest suite evidence cited inside some capsules (sanitizer/session/BatchBuilder batteries) was executed at this identical HEAD by a predecessor pass and is inherited, not re-executed, in pass 1.

## Full view (memory graph)
Revalidate `openreplay` before porting: run `index_status --verbose`, `check_index_coverage` (stdin JSON), `search_graph` (single positional JSON arg; no `--mode` flag exists), `trace_path`, `get_code_snippet`. Known caveats: BM25 search covers Function/Method nodes well but doc-shaped Section nodes need `search_code`; ee/ Python connector files carry an enterprise-license restriction on code copying (patterns are fair game); `top_observer.ts` ships conflict markers at this pin breaking 2 jest suites; `networkMessage.test.ts` TDZ defect (see Provenance). Source and direct tests decide shipped claims.

## Boundaries
Adopt pure contracts: sanitizer lattices, mask-as-length wire formats, proxy identity guards, clone/chunked response discipline, checkpoint/rewind encoder discipline, keepalive budgeting, token grace windows, consent FSMs. Adapt host-specific integration: storage keys, option names, framework shims, dialect loaders, signaling transports. Omit source-specific product behavior: SaaS endpoints (`api.openreplay.com`), cloud billing, frontend React dashboard, spot extension internals, mobile SDKs, and all `ee/` code beyond pattern reference.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`adopted-stylesheets-tracking.md`](./adopted-stylesheets-tracking.md)
- [`analytics-batcher-squash.md`](./analytics-batcher-squash.md)
- [`app-start-deferral-gate.md`](./app-start-deferral-gate.md)
- [`assist-identity-gate.md`](./assist-identity-gate.md)
- [`assist-overlay-canvas.md`](./assist-overlay-canvas.md)
- [`assist-remote-control-fsm.md`](./assist-remote-control-fsm.md)
- [`batch-builder-transactional-encode.md`](./batch-builder-transactional-encode.md)
- [`batch-writer-stream-routing.md`](./batch-writer-stream-routing.md)
- [`beacon-cache-ttl.md`](./beacon-cache-ttl.md)
- [`beacon-content-type-verdict.md`](./beacon-content-type-verdict.md)
- [`beacon-push-datatype-routing.md`](./beacon-push-datatype-routing.md)
- [`canvas-frame-packing.md`](./canvas-frame-packing.md)
- [`capture-rate-timestamps.md`](./capture-rate-timestamps.md)
- [`cold-start-dual-buffer.md`](./cold-start-dual-buffer.md)
- [`commit-recovery-ladder.md`](./commit-recovery-ladder.md)
- [`conditions-trigger-latch.md`](./conditions-trigger-latch.md)
- [`console-proxy-capture.md`](./console-proxy-capture.md)
- [`cross-tab-session-election.md`](./cross-tab-session-election.md)
- [`css-inliner-ladder.md`](./css-inliner-ladder.md)
- [`dom-sanitizer-lattice.md`](./dom-sanitizer-lattice.md)
- [`ee-connectors-dialect-dispatch.md`](./ee-connectors-dialect-dispatch.md)
- [`exception-normalization.md`](./exception-normalization.md)
- [`fetch-clone-chunked-ladder.md`](./fetch-clone-chunked-ladder.md)
- [`gzip-body-cap.md`](./gzip-body-cap.md)
- [`hmac-session-token-codec.md`](./hmac-session-token-codec.md)
- [`idle-callback-scheduler.md`](./idle-callback-scheduler.md)
- [`img-placeholder-resanitize.md`](./img-placeholder-resanitize.md)
- [`input-privacy-ladder.md`](./input-privacy-ladder.md)
- [`integration-token-obfuscation.md`](./integration-token-obfuscation.md)
- [`log-sanitizer.md`](./log-sanitizer.md)
- [`main-thread-gzip-offload.md`](./main-thread-gzip-offload.md)
- [`maintainer-node-gc.md`](./maintainer-node-gc.md)
- [`network-message-sanitize-order.md`](./network-message-sanitize-order.md)
- [`network-proxy-identity-guard.md`](./network-proxy-identity-guard.md)
- [`ngsafe-zone-shims.md`](./ngsafe-zone-shims.md)
- [`node-id-packing.md`](./node-id-packing.md)
- [`offline-recording-roundtrip.md`](./offline-recording-roundtrip.md)
- [`primitive-encoder-bytes.md`](./primitive-encoder-bytes.md)
- [`private-mode-redaction.md`](./private-mode-redaction.md)
- [`queue-sender-serial-upload.md`](./queue-sender-serial-upload.md)
- [`resanitize-subtree.md`](./resanitize-subtree.md)
- [`session-start-admission.md`](./session-start-admission.md)
- [`session-token-tab-identity.md`](./session-token-tab-identity.md)
- [`simple-merge-options.md`](./simple-merge-options.md)
- [`sink-filepool-lru.md`](./sink-filepool-lru.md)
- [`start-response-client-contract.md`](./start-response-client-contract.md)
- [`string-dictionary-attributes.md`](./string-dictionary-attributes.md)
- [`string-wiper-input-mask.md`](./string-wiper-input-mask.md)
- [`tag-watcher-matching.md`](./tag-watcher-matching.md)
- [`ticker-nth-turn.md`](./ticker-nth-turn.md)
- [`time-origin-clock.md`](./time-origin-clock.md)
- [`tracker-network-module-wiring.md`](./tracker-network-module-wiring.md)
- [`tracker-start-guards.md`](./tracker-start-guards.md)
- [`url-param-sanitizer.md`](./url-param-sanitizer.md)
- [`webrtc-call-choreography.md`](./webrtc-call-choreography.md)
- [`webworker-lifecycle-restart.md`](./webworker-lifecycle-restart.md)
- [`ws-channel-hook.md`](./ws-channel-hook.md)
- [`xhr-readystate-freeze-map.md`](./xhr-readystate-freeze-map.md)
