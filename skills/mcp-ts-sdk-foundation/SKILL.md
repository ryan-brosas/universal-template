---
name: mcp-ts-sdk-foundation
description: "Use when building MCP servers/clients: dual-era wire codecs, inbound validation ladders, era negotiation probes, per-request transports, response caching, and HMAC state tokens."
disable-model-invocation: true
---

# MCP TS SDK Foundation

## Use this for
MCP servers and clients: dual-era protocol classification, versioned wire codecs, connect-time era negotiation, the inbound validation ladder, per-request HTTP serving, client-side response caching, and multi-round-trip flows. Source and tests are the contract; references resolve to decisive excerpts and retrieval.
Server-side HTTP auth & validation: bearer-token gates with WWW-Authenticate challenges, RFC 9728/8414 discovery documents, Origin/Host allowlist defenses, and the core/adapter middleware layering that single-sources them across frameworks.

## Load the matching source dump
- `references/protocol.md` — Protocol base internals and correlation timeouts.
- `references/auth.md` — SEP-2352 issuer-stamped credential isolation, discovery, scope step-up, token-request enforcement.
- `references/refresh-persistence-boundary.md` — saveTokens-after-refresh failures propagate (#2053): persistence outside the refresh try/catch, invalidation warnings with JSON-stringified causes.
- `references/transports.md` — session lifecycle, store-first resumability, identity-checked teardown, reconnect rule, content negotiation.
- `references/inbound-ladder.md` — body-primary classification, ladder-as-data rungs, origin-keyed HTTP statuses.
- `references/envelope-claim-detection.md` — when a message claims the per-request `_meta` envelope.
- `references/wire-lift.md` — lifting reserved `_meta` keys / retry params so handlers see the legacy shape.
- `references/wire-codec-era-resolution.md` — many-to-one era→codec mapping with physical deletions.
- `references/outbound-bootstrap-pins.md` — pre-negotiation codec pins by method (ping unpinned).
- `references/era-handoff.md` — classified traffic landing on an instance of the wrong era refuses with −32022.
- `references/schema-preload-economics.md` — lazy vs module-scope schema construction per runtime billing model.
- `references/probe-verdict-classifier.md` — four-verdict taxonomy over one raw server/discover probe exchange.
- `references/stdio-sibling-probe.md` — disposable-sibling probing for servers that exit on pre-initialize requests.
- `references/cached-era-verdicts.md` — persist-modern-freely/date-legacy-mandatory gateway verdicts.
- `references/auth-seam-stamp.md` — Symbol.for throw-boundary provenance stamps surviving bundle duplication.
- `references/cross-bundle-brands.md` — brand-stamped error classes with Symbol.hasInstance across copies.
- `references/sdk-error-taxonomy.md` — local string SdkErrorCodes never serialize as numeric JSON-RPC codes.
- `references/response-cache.md` — generation-guarded writes, JSON-encoded partitions, scope-gated two-probe reads.
- `references/list-auto-aggregate.md` — fail-loud capped cursor walks writing one cache aggregate.
- `references/per-request-transport.md` — single-use transport with an observable dispatch window for status origin.
- `references/dual-era-entry.md` — fetch-handler composition: classify → gates → factory → invoke.
- `references/version-header-presence-gate.md` — SEP-2243 required-header presence enforced one rung AFTER body-primary classification (#2590): shared header read, request-only, version-header-missing first cell.
- `references/listen-router.md` — SSE subscriptions: ack-first frames, capability-narrowed filters, graceful-close signal.
- `references/request-state-codec.md` — MAC-first verify, version-bound MAC, tag-only binding, key snapshot at construction.
- `references/input-required-driver.md` — driver-over-manual-primitive MRTR loop: caps, pacing, linked round aborts.
- `references/legacy-input-shim.md` — cross-era MRTR emulation sharing primitives with the modern driver.
- `references/mcp-param-headers.md` — x-mcp-header scan (structural-reachability sweep) + mirror validation.
- `references/cache-hint-stamping.md` — symbol-carried config filled at encode time only on its era.
- `references/text-fallback.md` — TextContent auto-append + 2025-only {result:…} wrap for non-object structuredContent.
- `references/notification-coalescing.md` — opt-in microtask debounce of simple notifications.
- `references/cancel-wire-contract.md` — absence-exact request-id semantics (`0`/`''` legal), initialize never cancelled on the wire (#2654/#2668).
- `references/timeout-kernel.md` — restart-not-extend progress resets under an absolute total cap.
- `references/fetch-middleware.md` — composable FetchLike chain with 401 re-auth retry.
- `references/tool-name-grammar.md` — SEP-986 MUST/SHOULD split with character-level diagnostics.
- `references/completable-schema.md` — symbol-tagged autocompletion wrapper keeping StandardSchemaV1 validity.
- `references/bearer-token-gate.md` — verify ladder order, code→status/challenge mapping, expiresAt-required policy.
- `references/oauth-discovery-documents.md` — match-before-validate fall-through, 204/405/HEAD responder, path-aware well-known routes.
- `references/origin-allowlist-validation.md` — absent-pass/present-deny split, opaque-null rejection, exact hostname matching.
- `references/host-header-allowlist.md` — missing-denies + URL-API hostname extraction DNS-rebinding defense.
- `references/www-authenticate-challenge-builder.md` — sanitize-then-assemble quoted-string challenges hostile text cannot break.
- `references/core-adapter-middleware-split.md` — three-altitude split keeping auth decisions out of framework shells.
- `references/discovery-chain-composition.md` — one resourceServerUrl wiring 401 challenge → PRM route → AS discovery.
- `references/tools-call-validation-funnel.md` — dispatch-time codec resolution, family-scoped normalization, one projection window keeping listing and call aligned.
- `references/input-required-seam.md` — server-side input_required seam: era-split −32042 policy, at-least-one + envelope-capability re-checks, legacy-shim routing.
- `references/request-state-verify-hook.md` — requestState.verify placement: non-string gate runs unconfigured, frozen −32602 wire vs onerror-only reasons, load-bearing resolved payload.
- `references/push-api-era-guard.md` — guard-first typed local errors steering deprecated server→client push APIs to inputRequired before any wire traffic.
- `references/dual-era-logging.md` — per-request `_meta.logLevel` vs session `setLevel` thresholds; an absent threshold suppresses on 2026, means no-filter on 2025.
- `references/capability-preinstall.md` — eager handler install for declared capabilities (empty list answers, never Method-not-found), one-way latches, insertion-order listings.
- `references/update-handle-memoization.md` — closure-tracked registry keys + two-sided memo eviction on rename into occupied slots; warn-never-throw schema conversion at the boundary.
- `references/output-schema-gates.md` — structuredContent presence is `=== undefined` (any JSON legal), validating only the completing round, catch-all with exactly one rethrow escape.
- `references/completion-resolution.md` — optional-unwrapping completer discovery, uncapped `total` over 100-capped `values`, completions capability auto-enabled at registration.
- `references/resource-read-resolution.md` — exact-URI map then template scan, never-serialized cacheHint carriers, semantic domain errors whose wire code the encode seam owns.
- `references/elicitation-leg-split.md` — the capability-check-free, accept-unvalidated elicitation leg the legacy shim shares with the public API.
- `references/static-initializer-privilege-hooks.md` — class static-block closures handing serving entries private-state access without widening the package index.
- `references/stdio-era-negotiation.md` — classify-once-then-pin state machine: optimistic discover probe with an OPEN window, fallback discard, late-initialize refusal, teardown re-checks after every await.
- `references/stdio-channel-drain-latch.md` — pending-request set settling on answer or cancellation; bounded drain before discarding a probe so accepted requests are never dropped.
- `references/stdio-teardown-ordering.md` — graceful per-subscription results BEFORE transport close, independent per-leg error capture, three-trigger single-flight latch.
- `references/stdio-stream-discipline.md` — newline-framed read loop where parse failures survive but overflow/EPIPE closes; once-latched drain/error send; pause stdin only when last listener.
- `references/invoke-seam-composition.md` — connect-inject-capture per-exchange serving returning a real Response; authInfo strictly caller-passed, era state never written here.
- `references/sse-keepalive-arming.md` — invalid intervals disable rather than throw; >2^31−1 clamps instead of wrapping into a 1ms busy-spin; timers unref'd.
- `references/oauth-router-metadata-construction.md` — AS metadata derived from provider shape (register/revoke endpoints self-declare), https/no-query/no-fragment issuer grammar, path-aware well-known routes.
- `references/oauth-authorize-two-phase-errors.md` — pre-redirect 400s vs post-redirect error redirects; RFC 8252 §7.3 paired-loopback port relaxation.
- `references/oauth-iss-redirect-monkey-patch.md` — RFC 9207 `iss` injected by wrapping res.redirect; claim-vs-enforcement coupling with `authorizationResponseIssParameterSupported`.
- `references/oauth-token-pkce-skip-boundary.md` — PKCE XOR: verify locally OR forward code_verifier upstream, never both/neither; grant schema split.
- `references/oauth-client-registration-expiry.md` — public clients get no secret/expiry; expiry is data checked by middleware, never deleted by stores; stricter registration rate limits.
- `references/oauth-proxy-provider-delegation.md` — pass-through AS delegation matrix; retracts both unenforceable claims (`skipLocalPkceValidation`, iss support).
- `references/legacy-sse-transport-bracket.md` — deprecated SSE+POST transport lifecycle; clear-before-onclose teardown; opt-in DNS-rebinding header checks.
- `references/legacy-output-schema-ref-rewrite.md` — position-aware `$ref`/`$dynamicRef` pointer rewrite under the `{result:…}` wrap; `$id` scoping; `$schema` hoist; 2019-09 recursion limits.
- `references/standard-schema-conversion-stamps.md` — vendor-agnostic JSON Schema conversion with the provably-object output stamp; zod version fallbacks; format-pattern trust rule.
- `references/raw-shape-zod-triage.md` — plain-object raw-shape detection gates ordered so wrapped schemas/v3 schemas fail loud, not opaque.
- `references/client-capability-lattice.md` — `-32021` requirement diff preserving `ClientCapabilities` shape; bare `elicitation:{}` implies form; mode-aware input-request requirements.
- `references/bounded-uri-template-engine.md` — RFC 6570 subset compiler with four hard bounds; `?`→`&` continuation; anchored exploded matching without ReDoS.
- `references/content-type-essence-ladder.md` — parse-fallback-comma essence ladder; substring matching wrong in both directions; duplicate-header ambiguity ⇒ no classification.
- `references/resource-url-rfc8707-match.md` — fragment stripping at normalization; slash-padded segment-safe prefix matching.
- `references/contentless-result-family-guard.md` — foreign-family keys veto the `{content:[]}` default; leaf-module placement breaks a codec import cycle.
- `references/inmemory-linked-pair.md` — queue-before-start linked transport pair; peer-chained close with onclose-in-finally.
- `references/mcp-authextensions-clientcredentials-provider.md` — non-interactive provider skeleton: constructor-stamped SEP-2352 binding, throwing interactive-leg tripwires, sync prepareTokenRequest.
- `references/mcp-authextensions-privatekeyjwt-factory.md` — per-request `private_key_jwt` assertion minting: key-form import ladder, claim merge precedence, audience fallback chain, lazy jose import.
- `references/mcp-authextensions-privatekeyjwt-providers.md` — fresh-mint vs static-assertion twins sharing one skeleton; issuer=subject=clientId default.
- `references/mcp-authextensions-crossappaccess-provider.md` — discovery-state capture via optional hooks feeding an async jwt-bearer prepareTokenRequest (SEP-990).
- `references/mcp-crossappaccess-token-exchange.md` — RFC 8693 ID-Token→ID-JAG exchange: omit-don't-empty client secret, two-required-field response schema, TLS gate first.
- `references/mcp-crossappaccess-exchange-grant.md` — RFC 7523 leg: default-basic-with-loud-missing-secret, explicit none for public clients, shared applyClientAuthentication + assertSecureTokenEndpoint.
- `references/client-send-ladder.md` — POST exchange ladder: reserved-header veto, body-derived Mcp-* headers only under an envelope claim, ok-handshake session adoption (empty response clears stale id), parsed-media-type response branching.
- `references/modern-400-inband-delivery.md` — HTTP 400 + JSON-RPC error body delivered in-band only for modern-enveloped requests with matching ids; legacy exchanges keep SdkHttpError.
- `references/step-up-scope-union.md` — SEP-2350 insufficient_scope step-up: union(transport, token, challenge) scope, superset-gated refresh bypass (RFC 6749 §6), per-send bounded retry counter, 'throw' short-circuit.
- `references/sse-resume-reconnection-kernel.md` — three-gate resume predicate (reconnectable|priming ∧ ¬receivedResponse ∧ ¬intentionalAbort), server retry-field override vs capped backoff, scheduler hook cancelled by close().
- `references/sse-client-endpoint-bracket.md` — deprecated SSE client: start resolves on origin-checked endpoint event only; fetch-wrapper captures the 401 response for a single restart chain.
- `references/stdio-spawn-disposal-ladders.md` — allowlist env inheritance (function-values skipped, frozen pin), shell:false spawn, stdin.end→2s→SIGTERM→2s→SIGKILL close ladder, _dispose awaiting exit + destroying parent pipes.
- `references/client-auth-scope-helpers.md` — computeScopeUnion first-seen-order Set dedup (no hierarchical collapse) + isStrictScopeSuperset strict-exceeds gate; absent token scope counts EMPTY so step-up forces fresh auth.
- `references/client-www-auth-challenge-parse.md` — bearer-typed WWW-Authenticate reader: quoted-or-unquoted field regex, invalid resource_metadata URL dropped silently, non-bearer ⇒ {}.
- `references/oauth-callback-error-gate.md` — error-shaped OAuth callbacks issuer-gated BEFORE attacker-controlled error text surfaces; four-row RFC 9207 table; simple string equality only.
- `references/auth-provider-bridge.md` — AuthProvider vs OAuthClientProvider duck-type split, adaptOAuthProvider one-time bridge (token() carries no issuer ctx), handleOAuthUnauthorized retry-once chain.
- `references/client-connect-era-dispatch.md` — connect()'s three paths (prior/negotiated/plain-legacy), resume-vs-fresh branches, validatePrior-before-mutate hardening, ProbeWindow one-shot start() handover + spent-close-guard disarm ordering.
- `references/client-capability-posture.md` — two-tier capability enforcement: lenient empty-list defaults vs opt-in enforceStrictCapabilities funnel hook; ForMethod reads SERVER caps, HandlerCapability reads OWN caps.
- `references/readbuffer-framing-kernel.md` — shared newline framing kernel: overflow clear-then-throw before concat, SyntaxError lines skipped while schema failures throw.
- `references/listen-subscription-lifecycle.md` — subscriptions/listen caller FSM: 'listen:N' string-id namespace, single idempotent settle, dual-channel wireTeardown (requestSignal abort + notifications/cancelled), _onclose settles live subscriptions remote-side.

## Capsule map
- **Dual-era protocol** — `protocol`, `inbound-ladder`, `envelope-claim-detection`, `wire-lift`, `wire-codec-era-resolution`, `outbound-bootstrap-pins`, `era-handoff`: era is instance state; classifications validate, codecs own vocabulary; deletions are physical.
- **Wire & schema infrastructure** — `schema-preload-economics`, `cache-hint-stamping`, `text-fallback`, `notification-coalescing`, `cancel-wire-contract`, `timeout-kernel`: revision-required fields and coalescing added without touching the legacy wire; cancellation is absence-exact and initialize-silent.
- **Era negotiation (client)** — `probe-verdict-classifier`, `stdio-sibling-probe`, `cached-era-verdicts`: conservative verdict taxonomy, one-life subprocess probing, fleet-safe persistence.
- **Errors & provenance** — `auth-seam-stamp`, `cross-bundle-brands`, `sdk-error-taxonomy`: throw-boundary stamps and brand-set instanceof surviving duplicated bundles.
- **Caching & aggregation (client)** — `response-cache`, `list-auto-aggregate`: partitioning, race-guarded writes, capped walks.
- **HTTP serving (server)** — `per-request-transport`, `dual-era-entry`, `version-header-presence-gate`, `listen-router`: dispatch-window status origins, gate ordering, ack-first subscriptions; required-header presence rides one rung behind classification by design. `transports`: streamable-HTTP session lifecycle — missing-header ⇒ 400 vs unknown-session ⇒ 404 asymmetry, events stored BEFORE delivery so Last-Event-ID replays survive disconnects, client reconnect never cancels the logical session.
- **Multi-round-trip & headers** — `request-state-codec`, `input-required-driver`, `legacy-input-shim`, `mcp-param-headers`: HMAC state tokens, shared-primitive drivers, structural header sweeps.
- **Auth middleware & naming** — `auth`, `refresh-persistence-boundary`, `fetch-middleware`, `tool-name-grammar`, `completable-schema`: OAuth retry chains with propagation-safe persistence, SEP-986 grammar, sidecar completion metadata; `auth` carries the pass-1-era SEP-2352 issuer-stamped client credential isolation (loose pins — see Boundaries note).
- **Server auth & validation plane** — `bearer-token-gate`, `www-authenticate-challenge-builder`, `oauth-discovery-documents`, `discovery-chain-composition`, `origin-allowlist-validation`, `host-header-allowlist`, `core-adapter-middleware-split`: ladder-ordered token verification, fail-scoped discovery, deny-on-failure header defenses, single-sourced decision logic under per-framework shells.
- **Server core (low-level Server)** — `tools-call-validation-funnel`, `input-required-seam`, `request-state-verify-hook`, `push-api-era-guard`, `dual-era-logging`, `elicitation-leg-split`, `static-initializer-privilege-hooks`: the `_wrapHandler` funnel and input-required seam validate era-exactly above handler code; verify hooks freeze wire errors; removed push APIs die locally with migration steers; static-block closures let serving entries write private state.
- **High-level McpServer facade** — `capability-preinstall`, `update-handle-memoization`, `output-schema-gates`, `completion-resolution`, `resource-read-resolution`: declared capabilities pre-install handlers; live update-handles evict memoized conversions both sides of a rename; output validation keys on `=== undefined`; completers resolve through optional wrappers with uncapped totals; reads resolve exact-then-template with era-owned error codes.
- **Stdio serving plane** — `stdio-era-negotiation`, `stdio-channel-drain-latch`, `stdio-teardown-ordering`, `stdio-stream-discipline`, `sse-keepalive-arming`, `invoke-seam-composition`: classify-once-then-pin connection lifecycle over a drain-latched channel; graceful results precede transport close; the raw transport survives parse failures but closes on overflow/EPIPE; keep-alives clamp instead of wrapping.
- **Legacy OAuth AS (server-legacy)** — `oauth-router-metadata-construction`, `oauth-authorize-two-phase-errors`, `oauth-iss-redirect-monkey-patch`, `oauth-token-pkce-skip-boundary`, `oauth-client-registration-expiry`, `oauth-proxy-provider-delegation`, `legacy-sse-transport-bracket`: shape-derived endpoint advertisement, the pre/post-redirect error boundary, claim-vs-enforcement coupling, the PKCE XOR, expiry-as-data registration, and the upstream-delegation matrix that retracts both unenforceable claims.
- **Schema & capability kernel (core-internal)** — `legacy-output-schema-ref-rewrite`, `standard-schema-conversion-stamps`, `raw-shape-zod-triage`, `client-capability-lattice`, `bounded-uri-template-engine`, `content-type-essence-ladder`, `resource-url-rfc8707-match`, `contentless-result-family-guard`, `inmemory-linked-pair`: position-aware pointer surgery, provably-object stamps, loud zod-version triage, shape-preserving `-32021` diffs, bounded template compilation, parse-don't-substring content types, segment-safe resource matching, family-key vetoes, and the queue-before-start test transport.
- **Client auth extensions & cross-app access (pass 7)** — `mcp-authextensions-clientcredentials-provider`, `mcp-authextensions-privatekeyjwt-factory`, `mcp-authextensions-privatekeyjwt-providers`, `mcp-authextensions-crossappaccess-provider`, `mcp-crossappaccess-token-exchange`, `mcp-crossappaccess-exchange-grant`: non-interactive provider skeletons stamped with the SEP-2352 issuer binding; per-request JWT assertion minting over a key-form ladder; discovery-state capture feeding an async jwt-bearer request; RFC 8693/7523 layer-2 exchanges sharing `assertSecureTokenEndpoint` + `applyClientAuthentication`.
- **Client transports plane (pass 8)** — `client-send-ladder`, `modern-400-inband-delivery`, `step-up-scope-union`, `sse-resume-reconnection-kernel`, `sse-client-endpoint-bracket`, `stdio-spawn-disposal-ladders`: the client side of the wire — header authority with reserved-name veto and envelope-derived headers, ok-handshake-only session adoption, era-gated in-band 400 delivery, union-scope bounded step-up, the priming/response/abort reconnect gates over server-honored backoff, origin-checked endpoint resolution with captured-401 restart, and deadline+escalation process reaping with parent-pipe destruction.
- **Client facade & auth kernel (pass 9)** — `client-connect-era-dispatch`, `client-capability-posture`, `listen-subscription-lifecycle`, `auth-provider-bridge`, `client-auth-scope-helpers`, `client-www-auth-challenge-parse`, `oauth-callback-error-gate`, `readbuffer-framing-kernel`: one connect() entry dispatching cached-verdict/probed/plain-legacy paths with reset-before-handshake state hygiene; lenient-by-default capability posture with opt-in strict funnel hooks; a subscription FSM whose string ids cannot collide with request ids and whose settle funnels every termination once; the two-shape auth provider SPI bridged at transport construction; pure scope-union/challenge-parse helpers; issuer-gated callback errors; and the shared newline-framing kernel both stdio sides run on.

## Extending the foundation
Add one references-file-shaped capsule per new seam: one line in the loader, one map reference, decisive source, invariant, direct probe, and retrieval.

## Provenance
typescript-sdk (MIT), `main@3924de9` (`/mnt/hdd/utopia/inspo/typescript-sdk`; alias /home/utopia/work/inspo/typescript-sdk); Codebase Memory project `typescript-sdk` — full mode, 11,751 nodes / 45,813 edges, generation 2026-08-23T00:01:46Z, HEAD == base_sha == `3924de99df834302d89f5997a1b64ca268282284` (verified live at pass 8). TWIN RETIRED at pass 8: passes 5–7 cited the path-slugged twin `mnt-hdd-utopia-inspo-mcp-typescript-sdk` (canonical root then inspo/mcp/typescript-sdk, 11,829 nodes); the checkout has since moved to inspo/typescript-sdk, the twin no longer exists in the registry, and the re-baselined short-name project carries the same HEAD — older capsules' Retrieve blocks should substitute project `typescript-sdk` when replayed. Passes 2–4 mined `cc4b4161`; passes 5–7 mined `3924de9` (pass 6 = zero-drift depth pass: server-legacy OAuth AS + SSE plane and core-internal schema/capability kernel whole-file; pass 7 = client auth-extension + cross-app-access surface whole-file). Pass 8 = zero-drift client-transports depth pass: streamableHttp/sse/stdio client transports whole-file plus direct tests; check_index_coverage re-run on all eight newly-cited paths (all no_recorded_issue + metadata_match + generation_matches=true). Parse-partial caveats: 7 files (client/test/client/auth.test.ts:67, codemod ×5, core-internal exports/types/index.ts:1) — none among cited paths. Pass 9 = zero-drift client-facade + auth-kernel + framing depth pass: auth.ts helper plane exact ranges, client.ts connect/capability/listen lifecycle, versionNegotiation ProbeWindow handover, core-internal shared/stdio.ts ReadBuffer kernel; check_index_coverage re-run on all ten newly-cited paths (no_recorded_issue ×9; auth.test.ts partial at :67 read directly; auth.ts/protocol.ts freshness metadata_changed verified byte-identical to HEAD via empty `git diff --stat HEAD`). Facade correction: Client lives in client/client.ts, not the index.ts barrel named by pass-8 records.

## Full view (memory graph)
Revalidate Codebase Memory project `typescript-sdk` before porting (the live short-name project; the path-slugged twin `mnt-hdd-utopia-inspo-mcp-typescript-sdk` was retired at pass 8): run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. Pass-9 caveat: search_graph line ranges can drift from source (extractWWWAuthenticateParams graph :1418-1455 vs source :1456-1493) — always pin ranges from the file read.

## Boundaries
Adopt era-as-instance-state, physical registry deletion, probe verdict taxonomy, generation-guarded caching, MAC-first state verification, and the ladder/challenge ordering of the server auth plane; adapt transport adapters, auth providers, and HTTP frameworks to your host; omit the codemod suite, CLI/repl/examples surfaces, and the generated wire schemas unless porting them directly. The three pass-1 capsules (`protocol`, `auth`, `transports`) predate strict line pins — prefer their pass-2 successors for exact ranges where they overlap (`inbound-ladder`, `probe-verdict-classifier`, `per-request-transport`). The server-core plane (pass 4) mines the pin's server.ts/mcp.ts/serveStdio/stdio/invoke/sseKeepAlive whole; `createMcpHandler` internals stay with `dual-era-entry`, streamableHttp sessions with `transports`, and the shim/driver loops with their dedicated capsules. Pass 6 adds the legacy OAuth AS plane (server-legacy) and the schema/capability kernel (core-internal utils/shared); the legacy `requireBearerAuth` middleware is deliberately folded into the AS-plane capsules rather than duplicated beside the modern gate (`bearer-token-gate` owns the modern ladder), and `buildSchemas.ts` walls stay omitted as generated zod-schema data. Pass 7 adds the client auth-extension + cross-app-access plane (packages/client/src/client/{authExtensions,crossAppAccess}.ts whole-file plus their shared `auth.ts` primitives `applyClientAuthentication`/`assertSecureTokenEndpoint`); `authExtensions.examples.ts` is doc-snippet scaffolding for sync-snippets, and the shims/validators surfaces stay conditional as before. Pass 8 adds the client transports plane (packages/client/src/client/{streamableHttp,sse,stdio}.ts whole-file): the server-side streamableHttp sessions stay with `transports`, the server invoke seam with `per-request-transport`/`invoke-seam-composition`, and the listen driver's caller-side contract moved to `listen-subscription-lifecycle` at pass 9; there is no WebSocket client transport in this fork, and sse.ts's endpoint-origin check is source-visible but untested (pin it yourself if you port it).
