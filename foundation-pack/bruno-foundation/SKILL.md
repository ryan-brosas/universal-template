---
name: bruno-foundation
description: "Use when building API-client cores: TLS agent caching with LRU eviction, OAuth2 grant ladders + encrypted token vaults, PAC/system proxy resolution, cookie-jar wrappers, WebSocket connection FSMs, sandboxed expression interpolation."
disable-model-invocation: true
---

# Bruno Foundation

## Use this for
Use when porting an HTTP/API client engine: reusing TLS agents without leaking sockets, running OAuth2 grant flows with correct refresh/refetch/expired-token decisions, storing tokens encrypted at rest, driving embedded-browser authorization with CSRF-safe callbacks, resolving PAC scripts and system proxies, wrapping a shared cookie jar, keeping a long-lived WebSocket client race-free, interpolating user expressions safely, or making token-request failures visible in a debug timeline. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/agent-cache-lru.md` — hashed-key agent LRU (cap 100), destroy-on-evict, timeline repoint on cache hits, add-on-top secureContext so custom CAs don't replace the default store.
- `references/oauth2-token-lifecycle.md` — the valid → refresh → refetch → expired-but-requested ladder driven by `autoFetchToken`/`autoRefreshToken`, identical across electron/CLI/helper twins.
- `references/oauth2-credential-vault.md` — encrypted per-collection token store keyed `(url, credentialsId)` with lazy session-id minting and never-throw accessors.
- `references/oauth2-authorize-window.md` — BrowserWindow redirect interception: error-before-match ordering, response-indicator-gated callback matching, fail-closed state validation after close, exhaustive listener teardown; protocol-handler twin for deep links.
- `references/oauth2-pkce-state.md` — fresh-per-attempt PKCE S256 challenge; random-when-absent state with strict-equality check; the comment-vs-code divergence in `generateState`.
- `references/oauth2-additional-params.md` — enabled-gated header/query/body routing for token/refresh/authorize extras, pre-stringify body mutation, URL-reparse appends.
- `references/oauth2-debug-envelope.md` — every token attempt yields a main-request-shaped evidence entry; three-branch capture (success / HTTP error / transport errno).
- `references/vault-client-shim.md` — node-vault-compatible minimal Vault HTTP client: validateStatus-true classification, `/sys/health` status amnesty, dual-shaped `VaultError`, lazy TLS agents.
- `references/pac-resolver-cache.md` — promise-cache single-flight PAC downloads with TTL, self-evicting failures, QuickJS-sandboxed evaluation, injected `myIpAddress`.
- `references/system-proxy-merge.md` — env beats OS settings via `||` merge, single-flight OS detection, fail-open-to-env on detector failure.
- `references/proxy-normalization-safeexec.md` — execFile-only OS probing returning null on failure; idempotent scheme and no_proxy normalization.
- `references/cookie-jar-wrapper.md` — singleton jar wrapper: `__Host-` no-explicit-domain rule, Infinity expiry coercion, ignoreError sets, the callback-mode never-resolving-promise trap.
- `references/ws-client-fsm.md` — WebSocket lifecycle: CONNECTING-reuse, close-promise coalescing with 5s terminate fallback, queue-drop-before-handshake, identity-checked late close events.
- `references/sent-headers-reconcile.md` — read Node's `_header` block for what truly went out, length-mask proxy-authorization, additive case-insensitive merge into prepared headers.
- `references/header-delete-set-null.md` — script-driven header deletion must tombstone (`set(name, null)`) because axios's default-guard checks existence; host/connection protected.
- `references/timeline-agent-instrumentation.md` — subclass-wrapped agents logging DNS/TLS/ALPN events to a locally captured array (survives cached-agent repointing), errors carry partial timelines.
- `references/expression-interpolation.md` — compile-cached template literals: literal short-circuit ladder incl. MAX_SAFE_INTEGER string guard, keyword-filtered context destructuring.
- `references/ipc-clean-json.md` — realm-safe JSON sanitizer for cross-process payloads: circular refs, duck-typed Errors, typed-array envelopes, fail-open wrapper.
- `references/grpc-client-transport.md` — gRPC transport ladder: URL grammar (unix/pipe grpcs default), insecure-for-local + fail-closed rejectUnauthorized TLS, manual HTTP CONNECT proxy replication, stream-type dispatch, single-fire event latch, close-on-complete channel discipline.

## Capsule map
- **Agent reuse** — `agent-cache-lru`: Map keyed by classId+TLS hashes+proxy+hostname(nulled under proxy); LRU delete/re-set touch; evict ⇒ `.destroy()`; `ca` → cached shared SecureContext appended over OpenSSL defaults (pfx/cert/key build combined contexts).
- **Grant decisioning** — `oauth2-token-lifecycle`: stored-valid returns; expired tries refresh (failure clears store), then refetch if `autoFetchToken`, else deliberately ships the expired token; missing `expires_in` ⇒ assume valid forever.
- **Token storage** — `oauth2-credential-vault`: electron-store JSON with `encryptStringSafe` values; upsert = OR-filter by `(url, credentialsId)` then push; sessionId per collection isolates authorize partitions; all accessors swallow-and-log.
- **Authorize UX** — `oauth2-authorize-window`: hidden partition-scoped window; webRequest observers mutate one snapshot per main-frame nav; `?error=` rejects before callback matching; state validated fail-closed in the close handler; implicit tokens parsed from URL hash.
- **CSRF crypto** — `oauth2-pkce-state`: 22-byte-hex verifier → base64url SHA-256 challenge; user state returned VERBATIM despite comment claiming random suffix; mismatch rejects both in-window and via protocol handler.
- **Param injection** — `oauth2-additional-params`: `{enabled, name, value, sendIn}` gate-first routing; body slot mutates pre-`qs.stringify`; query slot reaparses URL; authorize slot is headers/query only.
- **Token observability** — `oauth2-debug-envelope`: `getCredentialsFromTokenUrl` returns `{credentials, requestDetails}` shaped like a main request; transport failures synthesize `status:'-'` entries carrying errno + attached timeline.
- **Secret resolution** — `vault-client-shim`: axios client with `validateStatus: () => true` and local classification; any `/sys/health/` path passes regardless of status (node-vault amnesty); `VaultError` carries both `statusCode` and aliased `status`; TLS agent built only when strictSSL/ca demand.
- **PAC plane** — `pac-resolver-cache`: CACHE stores PROMISES (single-flight); https keys add ca-hash/rejectUnauthorized/minVersion; failed downloads self-evict; resolve splits on `;`; QuickJS WASM sandbox with live-NIC `myIpAddress`; axios `proxy:false` fetches.
- **Proxy detection** — `system-proxy-merge`: lowercase>uppercase>ALL_PROXY env precedence wins every slot over OS detectors; OS probe is single-flight and degrades to env-only on failure.
- **Proxy hygiene** — `proxy-normalization-safeexec`: execFile-only OS probing returning null-on-failure; idempotent scheme prepending (`http://` only when unschemed) and `[;,\s]+`→comma no_proxy normalization.
- **Cookie plane** — `cookie-jar-wrapper`: dual-mode (callback/promise) methods where callback mode MUST NOT return tough-cookie's never-resolving promise; `__Host-*` cookies omit explicit domain so tough-cookie derives hostOnly; expired filtered at read; setCookie ignores errors.
- **WS reliability** — `ws-client-fsm`: four maps (active/closing/queues/keepalives); start awaits in-flight close then reuses CONNECTING|OPEN sockets; close coalesces onto one promise, drops queue pre-handshake, terminates after 5s; late socket events identity-checked so replacements survive.
- **Wire truth** — `sent-headers-reconcile`: parse `_header` skipping request line, first-colon split preserving colons in values; proxy-auth masked to value length; merge adds-only case-insensitively.
- **Header deletion** — `header-delete-set-null`: script-driven deletions tombstone as `set(name, null)` because axios's default-guard tests existence; host/connection are protected transport names.
- **Connection telemetry** — `timeline-agent-instrumentation`: subclass captures `this.timeline` into a local at createConnection entry; logs ALPN offer, CA counts, DNS, cipher suite, peer cert; thrown errors get `.timeline` attached; wrapper classes WeakMap-memoized.
- **Expression runtime** — `expression-interpolation`: expression compilation cached per raw string with globals shimmed from globalThis; template ladder short-circuits literals and >MAX_SAFE_INTEGER numbers.
- **Cross-process payloads** — `ipc-clean-json`: cleanJson makes sandbox objects Electron-transmittable via realm-safe Error duck-typing, WeakSet cycles, typed-array envelopes, fail-open wrapper.
- **gRPC plane** — `grpc-client-transport`: Bruno-specific gRPC client (unix/named-pipe/TCP URL ladder, proto-loader long→string precision, reflection v1/v1alpha fallback, stream method dispatch, close-on-complete channels).

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question — pass-2 candidates: node-vm sandbox CJS loader (`packages/bruno-js/src/sandbox/node-vm/cjs-loader.js`), bru shims (`sandbox/quickjs/shims/bru.js` 580L), error-formatter (752L + spec 1,073L), assert-runtime (585L), collection transpiler units (`bruno-lang`), import converters OpenAPI/Postman (`bruno-converters`). Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
bruno (MIT), `main@675965612ff11b23bc9b6c9541110a287bcb2967` (= base_sha, first pass, zero drift); Codebase Memory project `ext-bruno` (ready, root `/mnt/hdd/utopia/inspo/external/bruno`, branch main@same sha, 27,553 nodes / 96,755 edges, FULL mode, generation 2026-08-23T11:39:47Z generation_matches=true; parse_partial ×12 = JSX story pages/Dockerfiles/malformed-import FIXTURES — none cited; not_indexed ×32 = images/.env BY DESIGN).

## Full view (memory graph)
Revalidate `ext-bruno` before porting: run `index_status --project ext-bruno --verbose`, `check_index_coverage` (stdin JSON), `search_graph`, `trace_path`, `get_code_snippet`. Root `/mnt/hdd/utopia/inspo/external/bruno`, branch `main@67596561`, 27,553 nodes / 96,755 edges. All 17 cited source paths reported `no_recorded_issue` + `metadata_match` on check_index_coverage at this pin. Graph retrieval verified live: `getOrCreateAgentInternal` :230-303, `getPacResolver` :73-126, `WsClient.startConnection` :70-149 / `close` :216-268 / `closeForCollection` :288-299, `SystemProxyResolver.detectByPlatform` :55-66, `hasHostPrefix` :11 / `cookieJarWrapper` :186-530, `getOAuth2Token` :319-399 (+electron twin `isTokenExpired` :41-50), `handleOauth2ProtocolUrl` :46-132, `generateCodeChallenge` :727-735. Direct-test coverage is strong in bruno-requests: agent-cache.spec (key-separation + timeline-repoint matrix), oauth2-helper.spec (:67-475 placement matrix), pac-resolver.spec (:55-270 incl. TTL/file://-Windows paths), cookies/index.spec (callback-not-Promise contract), ws-client.spec (:91-272 seven named race scenarios), sent-headers.spec (live-server round-trip), node-vault.spec (:696-716 health amnesty), system-proxy index/linux/common specs. Coverage caveats recorded in-capsule: Oauth2Store, authorize-window, protocol-handler, axios-instance, cleanJson have no dedicated unit specs (verified against whole-file source reads + upstream integration tests). Runner note: inspo clone ships no installed workspace deps; probes executed as deterministic grep/anchor checks against cited specs rather than a jest run.

## Boundaries
Adopt the agent-LRU contract (hashed keys, destroy-on-evict, add-on-top CA contexts), the OAuth2 flag ladder with clear-poisoned-refresh semantics, encrypted triple-keyed token storage, fail-closed state validation, promise-cache single-flight PAC resolution, env-beats-OS proxy merging, `__Host-` jar discipline, the WS close-coalescing FSM, and the compile-cached interpolation ladder. Adapt Electron-specific plumbing (BrowserWindow, partitions, electron-store), axios/tough-cookie specifics, and debug-entry shapes to your host. Omit the React app surface (`bruno-app` UI components), the Electron main-process IPC registration boilerplate, collection-file format tooling (`bruno-lang`/`bruno-filestore`, queued pass-2), gRPC client internals (queued pass-2), and Playwright e2e harness unless your target needs them.
