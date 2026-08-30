---
name: copilotkit-foundation
description: "Use when building a multi-platform chat/channel agent runtime (Slack, Teams, Discord, Telegram, WhatsApp) or cross-platform UI bridge — dynamic Proxy subscriber fanouts, isolated error boundaries between runners and renderers, symbol-branded terminal delivery errors, durable action registry rehydration with payload-limited value caching, thread promise conversion boundaries, stream null-string sanitization for LangGraph tool interrupts, sentinel-based Markdown-to-mrkdwn pipelines, per-platform transport planes (Discord ack-race chunking, Teams proactive turns + Adaptive Cards, WhatsApp signed webhooks), core RunHandler run-loop contracts, realtime-gateway connection-health machinery, channel-delivery packet transport stack, and universal UI Intermediate Representation (IR) AST expanders. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."
disable-model-invocation: true
---

# copilotkit: Multi-Channel Agent & UI Runtime Foundation

## Use this for
Use when building a multi-platform chat/channel agent runtime (Slack, Teams, Discord, Telegram, WhatsApp) or cross-platform UI bridge: dynamic `Proxy` subscriber fanouts, isolated error boundaries between runners and renderers, global symbol-branded terminal delivery errors, dual-tier durable action registries with payload-limited value caching, thread promise conversion boundaries, stream null-string sanitization for LangGraph tool interrupts, sentinel-based Markdown-to-mrkdwn pipelines, and universal UI Intermediate Representation (IR) AST expanders. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/agent-run-loop-subscriber-proxy.md` — dynamic `Proxy` subscriber fanout, dual execution error boundaries (`invokeSubscriberPair`), and event canonicalization with `WeakMap` memoization.
- `references/terminal-delivery-error-taxonomy.md` — global symbol-branded `ChannelDeliveryTerminatedError` preventing model-visible delivery error leakage and enforcing immediate turn termination.
- `references/action-registry-durable-rehydration.md` — dual-tier hot/durable action registry, server-side value caching for 64-byte payload limits, and component snapshot rehydration.
- `references/thread-adapter-promise-boundary.md` — promise boundary conversion guaranteeing synchronous adapter exceptions always yield rejected promises.
- `references/stream-event-null-string-coercion.md` — stream event null-string sanitization for LangGraph tool interrupts (`parentMessageId: null`) preventing schema re-validation aborts.
- `references/markdown-to-mrkdwn-sentinel-pipeline.md` — 5-phase sentinel markdown-to-mrkdwn converter protecting code fences and formatting GFM tables into aligned monospace blocks.
- `references/channel-ui-intermediate-representation.md` — universal UI Intermediate Representation (IR) and recursive AST expander supporting native payloads and key propagation.
- `references/discord-interaction-ack-race.md` — timer-race interaction acking inside Discord's 3s window: dual registries (component vs slash-command), latched single-response arbitration, modal-before-auto-defer, exactly-one-ack guarantee.
- `references/chunked-stream-frozen-boundaries.md` — splitting unbounded agent replies across N hard-limited messages with frozen chunk boundaries, soft-limit-below-hard-limit transform headroom (1900 vs 2000), block-keeps-whole fence rescue, and single-recorded setup errors.
- `references/markdown-auto-close-and-reopen.md` — sentinel-masked auto-closing of unfinished markdown mid-stream (push-index stack scan, content-gated closers) paired with context re-openers for continuation chunks.
- `references/discord-streaming-history-hygiene.md` — placeholder lifecycle hygiene (shared consts, finally-drain on stream failure), thread-starter rescue from the parent channel, reaction channelId fallback, cache-on-success-only user resolution.
- `references/discord-command-registration-race.md` — stash-plus-dual-publish-site command registration that survives READY-vs-register ordering and never issues an empty destructive PUT.
- `references/teams-detached-proactive-turn.md` — ack-immediately/detach-via-conversation-reference so HITL suspends outlive the HTTP turn; credential-gated dual path (proactive vs Playground); typing heartbeat every 3.5s.
- `references/teams-streamed-by-edit-throttle.md` — post-then-edit streaming with trailing-edge throttle AND serial promise queue (both required: one kills rate-limit 429s, the other kills stale-prefix races); fail-loud final flush.
- `references/adaptive-card-total-renderer.md` — total IR→Adaptive Card lowering: reserved routing ids (`ckActionId`/`value` pre-seeded), collision-free field-id ladder, budget clamps everywhere, unknown intrinsics skipped.
- `references/teams-native-jsx-codec.md` — provider-native JSX validated loud (single root, cross-provider refusal, version floor) then serialized byte-faithful; raw objects must be non-interactive.
- `references/whatsapp-webhook-verify-signature.md` — Meta handshake (challenge echo) + raw-byte HMAC verification (length-gate before timingSafeEqual) + ack-before-process ordering that defeats retry-storm webhook disabling.
- `references/whatsapp-no-edit-capability-fallbacks.md` — honest degradation for edit-less/delete-less/no-stream channels (re-post, no-op, buffer-all) plus wamid-keyed outbound journaling that keeps quote-replies resolvable.
- `references/follow-up-depth-circuit-breaker.md` — `MAX_FOLLOW_UP_DEPTH` recursion cap over `_runDepth`: abort-check-before-depth, framework-update yield before follow-up reads, warning naming the `followUp:false` remedy.
- `references/continuation-runid-wire-rule.md` — internal continuations must NOT pin the originating runId on the wire (transport re-delivers the completed run's applied half); logical-run identity lives in state management, wire identity per invocation.
- `references/connect-restore-churn-gate.md` — threadId-delta restore gate: fresh restores clear messages/state/cursors, same-thread churn preserves local view and resumes from `lastSeenEventId`; active-run detach stays unconditional.
- `references/frontend-tool-dispatch-ladder.md` — specific→wildcard(`*`) tool resolution with memoized wildcard lookup, `"Forwarded to client"` placeholder splice-and-reexecute, tool-result insertion past sibling results, thread-switch race guard.
- `references/capability-override-keys.md` — NUL-keyed external override sets (`agentId\u0000name`) so Inspector disables survive hook-driven re-registration; four-gate buildFrontendTools filter.
- `references/abort-suppression-ladder.md` — three-path abort classification (connect string ladder, own-controller-first subscriber rule, event-code fallback) keeping user stops banner-free while lock errors still surface.
- `references/tool-args-and-schema-normalization.md` — empty/nullish args coerce to `{}` observably, non-objects throw for attribution; tool schemas drop `$schema` + recursively strip `additionalProperties` (hard regression contract).
- `references/gateway-connect-watchdog-diagnosis.md` — everConnected-keyed connect watchdog + unauthenticated same-origin HTTP probe distinguishing NXDOMAIN (fail now) from booting gateway (wait window); healthy connects issue no probe.
- `references/gateway-health-fsm-sticky-gaveup.md` — sticky `gave_up` latch armed once per outage episode, healed only by successful REJOIN; episode-stamped outage probes prevent cause misattribution.
- `references/drop-dedupe-and-error-recovery.md` — episode-latched onClose dedupe across socket+channel hooks with reopen reset, 100ms error-without-close grace cycle, code-1000 override, pre-join invitation buffer (1,000 cap).
- `references/provider-state-fold-failopen.md` — five-state attachment vocabulary folded BEST-of across unconditionally-declared adapters; absent/malformed reply degrades to `undefined`, never "not attached"; dual-package PROVIDER_LEGS mirror.
- `references/transcript-fetch-retry-contract.md` — fixed-3-attempt transcript client: transport throws retry silently, invalid 200 bodies fail fast non-retryable, 429/5xx retry per server hint; per-delivery memoization.
- `references/tracked-promise-terminal-sealing.md` — ObservableTrackedPromise records rejection consumption so sealAndWait drains all Thread operations and blocks `complete` terminals on unobserved failures without unhandled-rejection noise.
- `references/surface-gated-failure-effects.md` — three-gate generic-failure ladder (expected output ⇒ promised surfaces ⇒ mention/welcome/interaction inputs) + `failed_before_output` vs `failed` classification via hasProviderOutput.
- `references/delivery-id-grammar-and-bounds.md` — `pref_v1_` opaque capabilities vs `pid_v1_` correlation ids, exact-field destination-free packet validation, 64KiB cap, shared UTF-8 reaction bound.
- `references/delivery-packet-exact-ordering.md` — tail-chained FIFO enqueue, exact-ack (deliveryId+seq+packetId) before seq advance, identical-packet retry across reconnects with capability-aware fullText strip.
- `references/delivery-claim-supersession-ladder.md` — claim-defer loop → one-use join-token → per-thread tails + global execution slots (abort-aware waiters), identity-checked tail cleanup, delivery_superseded aborts exactly the old claim.
- `references/gateway-launcher-activation-planes.md` — control-vs-delivery plane composition; connection health ("can we send") and provider attachment ("is it bound") never substitute; retry classification off typed unreachable/join errors.

## Capsule map
- **Agent Run Loop & Event Fanout** — `agent-run-loop-subscriber-proxy`, `stream-event-null-string-coercion`: Proxy subscriber fanouts, isolated ingestion/rendering boundaries, LangGraph SSE event coercion.
- **Delivery Error & Promise Boundaries** — `terminal-delivery-error-taxonomy`, `thread-adapter-promise-boundary`: Symbol.for branding, fail-closed turn abortion, async rejected promise guarantees.
- **UI Actions & State Rehydration** — `action-registry-durable-rehydration`: Hot in-memory caching, durable component snapshots, size-limited payload fallbacks.
- **Channel Formatting & UI AST** — `markdown-to-mrkdwn-sentinel-pipeline`, `channel-ui-intermediate-representation`, `markdown-auto-close-and-reopen`: Sentinel mrkdwn formatting, monospace table alignment, recursive IR expansion, streaming-safe markdown balancing.
- **Discord Transport Plane** — `discord-interaction-ack-race`, `chunked-stream-frozen-boundaries`, `discord-streaming-history-hygiene`, `discord-command-registration-race`: 3s-window ack racing, frozen-boundary chunking under a 2000-char cap, placeholder-free history reconstruction, race-proof command publication.
- **Teams Transport Plane** — `teams-detached-proactive-turn`, `teams-streamed-by-edit-throttle`: Detached proactive contexts for HITL suspensions, throttled + serialized edit streaming.
- **Teams Rendering Plane** — `adaptive-card-total-renderer`, `teams-native-jsx-codec`: Total budget-clamped IR→card lowering plus loud-validation native passthrough.
- **WhatsApp Transport & Security Plane** — `whatsapp-webhook-verify-signature`, `whatsapp-no-edit-capability-fallbacks`: Signed-webhook intake with ack-before-process, honest capability degradation with quote-reply journaling.
- **Core RunHandler Plane** — `follow-up-depth-circuit-breaker`, `continuation-runid-wire-rule`, `connect-restore-churn-gate`, `frontend-tool-dispatch-ladder`, `capability-override-keys`, `abort-suppression-ladder`, `tool-args-and-schema-normalization`: recursion cap, logical-vs-wire run identity, churn-vs-restore gate, specific/wildcard dispatch, re-registration-proof overrides, abort suppression, args/schema normalization.
- **Realtime Gateway Health Plane** — `gateway-connect-watchdog-diagnosis`, `gateway-health-fsm-sticky-gaveup`, `drop-dedupe-and-error-recovery`, `provider-state-fold-failopen`, `transcript-fetch-retry-contract`: connect watchdog + HTTP diagnosis, sticky gave_up FSM, episode-latched drop notifications, fail-open provider-state fold, transcript retry classes.
- **Channel Delivery Transport Stack** — `delivery-id-grammar-and-bounds`, `delivery-packet-exact-ordering`, `tracked-promise-terminal-sealing`, `surface-gated-failure-effects`, `delivery-claim-supersession-ladder`, `gateway-launcher-activation-planes`: packet grammar, exact-ack ordering, terminal sealing, surface-gated failure effects, claim/supersession admission, launcher activation planes.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
copilotkit (MIT), `main@e9387e04835545c45744b791aee7c9c03520be31`; Codebase Memory project `ext-copilotkit` (157,698 nodes / 582,076 edges, full mode, indexed 2026-08-23T00:00Z; zero parse_partial on cited packages).

## Full view (memory graph)
Revalidate `ext-copilotkit` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt the Proxy subscriber fanout, symbol-branded delivery error taxonomy, durable action registry rehydration, sentinel mrkdwn formatting pipeline, the Discord/Teams/WhatsApp transport-plane contracts, and the pass-2 second-shift planes (RunHandler run-loop contracts, gateway health machinery, delivery packet transport stack) captured in references. Adapt channel connection transports and webhook verification per host platform. Omit legacy v1 deprecated runtimes (`packages/runtime/src/v1-deprecated/`) and product examples unless specifically required.

## Extending backlog (pass-3 candidates, only past `e9387e04`)
Pass 2 (second-shift lane) mined `packages/core/src/core/run-handler.ts` whole and `channels-intelligence` src whole; `channels-telegram` (6.4kL: listener long-poll plane, chunked-edit-stream, interaction keyboard grammar) remains UNMINED. Also queued as named-porting-question targets: `channels-discord/render/components-v2.ts` + `render/modal.ts`, teams `download-files.ts`/`graph-files.ts` (Graph SharePoint fetch ladder), whatsapp `render/message.ts` interactive lowering, `packages/core/src/{memory.ts,threads.ts,intelligence-agent.ts,micro-redux.ts}` state plane, `runtime/src/v2/runtime/core/channel-manager.ts` fold consumer, react-core v2 chat components.
