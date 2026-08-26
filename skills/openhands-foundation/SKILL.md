---
name: openhands-foundation
description: "OpenHands Agent Canvas UI conversation runtime — dual-socket event streaming with REST-preload gating, rAF delta coalescing, id-dedup replay handling, optimistic message queues, cron-preset automation schedules, browser-executed client tools with exactly-once launch ledgers, backend-split REST services with compensating import transactions, scoped query-cache invalidation, contract-fixture MSW mock fleets, desktop boot-splash launch chains, bootstrap version gates, start-conversation payload translation, replay-safe client-action dispatch, local dev-stack launch orchestration, read-only terminal projection, and rate-budgeted run-health dashboards."
---

# OpenHands (Agent Canvas): agent-conversation UI runtime foundation

## Use this for
Use when building or porting an agent-chat frontend: resumable WebSocket event streams with REST history preload, token-stream coalescing, optimistic user bubbles with server-echo matching, replay-safe side effects, reconnect ladders for parallel sockets, or human-editable cron schedule pickers. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/conversation-stream-kernel.md` — How does a client subscribe to an agent event stream without re-receiving preloaded history, and survive refetch/reconnect races?
- `references/websocket-reconnect-ladder.md` — How do parallel sockets retry without lockstep thundering-herd, stale sockets clobbering fresh ones, or hung handshakes blocking the host?
- `references/streaming-delta-batcher.md` — How do per-token stream deltas commit at most once per frame while never letting durable events overtake their own streamed text?
- `references/event-store-dedup-projection.md` — How does a global event store dedup replayed backlogs, stay O(1) under token floods, and swap conversations atomically?
- `references/optimistic-user-message-queue.md` — How does an optimistic "Sending…" bubble get cleared by the right server echo and never hang forever?
- `references/automation-cron-preset-mapping.md` — How can a schedule editor round-trip cron strings to friendly presets without silently rewriting unsupported expressions?
- `references/client-tool-roundtrip-protocol.md` — How does a web UI execute an agent tool call locally, report the result back through the conversation, and stay exactly-once across event-stream replays?
- `references/dev-stack-launch-orchestrator.md` — How does an npm-launched full-stack script start a Python server + Vite frontend safely against port conflicts, cached wheels, reaped tmp sockets, and hard-killed predecessors?
- `references/read-only-terminal-projection.md` — How is a live agent terminal rendered as a disposable xterm projection of an event-sourced command store without fit crashes or remount history loss?
- `references/run-health-fanout-polling.md` — How does an N-card dashboard poll every item's latest run within a bounded request budget and degrade to "unknown" instead of lying?
- `references/backend-split-automation-service.md` — How does one thin REST client serve a local sidecar and a cloud host through one class, and keep an import's POST→PATCH→cleanup pinned to one backend?
- `references/automation-cache-scope-invalidation.md` — How should query keys be scoped so backend switches refire fetches automatically while one invalidation busts every pagination slice?
- `references/msw-contract-fixture-fleet.md` — How does a browser mock fleet ship zero prod bytes, install before any query, and stay byte-faithful to a published API contract?
- `references/desktop-boot-splash-chain.md` — How does an Electron shell start a local full stack with staged readiness, a startup-log splash, and cross-platform cleanup of detached children?
- `references/agent-server-version-gate.md` — Where should frontend/backend compatibility be enforced, against which host, and how do "too old", "unknown version", and "unreachable" differ?
- `references/start-conversation-payload-translation.md` — How does an adapter build one conversation-start payload for inline agents, server profiles, and ACP subprocesses without leaking secrets or tools across paths?
- `references/client-event-dispatch-pipeline.md` — In a socket handler that projects events AND fires non-idempotent effects, where must replay dedup sit?

## Capsule map
- **Conversation stream kernel** — `conversation-stream-kernel`: gate the WS on first-load `isPending` only; subscribe `resend_mode='since'&after_timestamp=<tail>` with `'all'` fallback; WS-down sends queue via REST with `{queued:true}`.
- **Reconnect ladder** — `websocket-reconnect-ladder`: 1s→30s exponential backoff + ≤30% jitter per socket instance; WeakSet membership gates which socket may reconnect; 10s CONNECTING watchdog; auth sent as first WS frame.
- **Delta batcher** — `streaming-delta-batcher`: injectable-frame scheduler coalesces adjacent deltas into one commit; `flush()` before any non-delta event preserves ordering; `reset()` drops buffers on switch.
- **Event store** — `event-store-dedup-projection`: zustand store dedups by event id, excludes transient deltas from the id Set, sorts only when out-of-order, and clears+rebinds conversations in one atomic set.
- **Optimistic queue** — `optimistic-user-message-queue`: pending bubbles scoped by conversationId; exact-content echo match with FIFO fallback; 150s timeout watchdog flips stuck sends to error.
- **Cron preset mapping** — `automation-cron-preset-mapping`: strict single-int/dow pattern recognition falls back to `kind:'custom'` so editors round-trip without rewriting user schedules.
- **Client-tool round trip** — `client-tool-roundtrip-protocol`: agent-server ACKs client tools before work → prefixed user message carries result/guidance; localStorage claim ledger makes non-idempotent launches replay-safe; enum-gap validation; goal-loop send suppression.
- **Dev-stack orchestrator** — `dev-stack-launch-orchestrator`: named-port fail-fast preflight, same-ref uvx ladder (--reinstall on git refs), persisted 0600 keys, liveness-gated stale owner_lease cleanup, SIGTERM→SIGKILL shutdown.
- **Terminal projection** — `read-only-terminal-projection`: store-owned history + watermark replay into xterm; five-clause canFit ladder under rAF-debounced ResizeObserver; CSS-var foreground probe.
- **Run-health fan-out** — `run-health-fanout-polling`: per-item useQueries sharing the runs key prefix (dispatch invalidations hit both), 15 s poll only while latest run non-terminal, retry:false → "unknown", forward-compatible default status fold.
- **Backend-split service** — `backend-split-automation-service`: per-call cloud-proxy vs local-axios split; call-time backend resolution with an explicit-pin escape hatch; placeholder-trigger import transaction with compensating delete + AggregateError; fail-soft health/version probes; raw-byte upload bypassing a JSON-only proxy.
- **Cache scope & invalidation** — `automation-cache-scope-invalidation`: read keys embed backend id + org id, invalidations fire on the bare prefix — one mutation busts every page/scope without cross-backend leakage.
- **MSW contract fixtures** — `msw-contract-fixture-fleet`: gate → dynamic import → start before hydration; capabilities answered from published contract fixtures; it.each replays every recorded preflight exchange; strict `"true"` env gate.
- **Desktop boot splash** — `desktop-boot-splash-chain`: bundled-runtime PATH injection (+x repair), two-bar readiness (<500 vs 200/401 end-to-end), bounded replayed boot log over batched IPC, emit-not-kill Windows shutdown with force-exit net.
- **Version gate** — `agent-server-version-gate`: probe the EFFECTIVE LOCAL host only; three-way taxonomy (Unsupported / Unknown / Unavailable) with hand-rolled semver incl. prerelease ordering; host-scoped cache; public-mode protected-endpoint re-probe.
- **Payload translation** — `start-conversation-payload-translation`: agent_profile_id XOR agent_settings enrichment boundary; client_tools only for openhands-kind launches; secrets as host-relative LookupSecrets in request.secrets ONLY; secrets_encrypted ACP exception; client-side metadata hydration on read.
- **Dispatch pipeline** — `client-event-dispatch-pipeline`: intercept deltas → flush before durable events → snapshot eventIds BEFORE addEvent → early-return gates every side effect → guard-routed effects (banner/telemetry/model-switch/client tools).

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
OpenHands / All-Hands-AI (MIT), `main@8511fff62d3084587cda1add483fe5ea9c8bfd7e` (`@openhands/agent-canvas` v1.15.0); Codebase Memory project `openhands` (FULL mode, 16923 nodes / 60281 edges, generation 2026-08-24T16:13:32Z; root+HEAD match pin; 36 parse-partial files are UI test fixtures/helm YAML/tailwind css — none cited here). Passes 1–3: 17 capsule-v2 references.

## Full view (memory graph)
Revalidate `openhands` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt the event-stream lifecycle contracts (preload gate, since-subscribe, dedup, batching, optimistic matching) as pure state machines; adapt the zustand/TanStack/React specifics and the `@openhands/typescript-client` REST calls to your host stack; omit the product surface (Agent Canvas UI panels, electron packaging, OpenHands cloud provisioning semantics).
