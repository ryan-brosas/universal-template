---
name: dsh-codex-foundation
description: "Use when porting ChatGPT-OAuth Codex provider machinery — provider-native auth adapters, single-flight browser login, cancellation and status recovery, exact-origin Web OAuth routes, CLI device-code selection, bounded Fast Mode state, quota parsing, search, image tools, Responses API policy, model-catalog settings, SSRF-guarded public HTTP loading, durable search-request session events, boot-free CLI JSON diagnostics, terminal /codex command internals (background login controller, headless-aware browser launch, redaction-bounded handler), client UI plane (slot-injected browser entry, settings OAuth lifecycle, fail-soft quota projection, fast-mode toggle, imagegen tool view), binary publication plane (sandbox-checked byte writes, atomic temp-file publish under per-path promise locks), server-side settings/Fast-Mode route gates over one bounded-body kernel, OAuth-bearer/factory/catalog adapter assembly, search config-overlay defaults, version-injection/composition-patch/release-provenance build plumbing."
disable-model-invocation: true
---
# dsh-codex: OpenAI Codex Subscription Provider Foundation

## Use this for
Use when building a ChatGPT-subscription-backed LLM provider adapter: provider-native OAuth delegation with secret-free status, single-flight browser challenges, cancellation-before-delete cleanup, quota-aware auth recovery, exact-origin Web OAuth route authorization, CLI browser/device-code selection, a bounded per-session Fast Mode registry, owner-only credential persistence, standalone web search, image-tool policy, Codex WebSocket/native-compaction transport selection, secret-free doctor diagnostics, and related Codex settings. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/auth-provider-adapter.md` — one porting question: one-provider OAuth delegation, logout, and a secret-free read-only status projection.
- `references/web-auth-challenge.md` — one porting question: single-flight browser login, validated HTTPS authorization challenge, waiter fan-out, and bounded timeouts.
- `references/web-auth-cancellation.md` — one porting question: abort active auth, settle every waiter, drain provider work, then delete on sign-out but not disposal.
- `references/auth-status-recovery.md` — one porting question: keep authentication separate from quota/reauth failures and recover stored sign-in after a failed browser flow.
- `references/trusted-origin-gate.md` — one porting question: loopback defaults plus exact remote-origin sidecar checks that fail closed.
- `references/trusted-origin-store.md` — one porting question: owner-only exact-origin allowlist persistence with fail-closed document validation, lock-serialized mutations, and detached sorted results.
- `references/auth-route-contract.md` — one porting question: exact auth endpoints that authorize before side effects and dispose through the host effect.
- `references/cli-auth-device-code.md` — one porting question: explicit CLI browser/device-code selection, signal forwarding, safe event output, and mode validation.
- `references/fast-mode-registry.md` — one porting question: bounded positive-only per-session boolean state with touch-on-read LRU eviction, and a streamSimple decorator that merges `service_tier: 'priority'` into the (possibly replaced) payload for the owning provider only.
- `references/usage-quota-parsing.md` — one porting question: secret-free projection of a provider quota/usage response with fail-closed numeric validation and fixed reauthorization error.
- `references/credential-store.md` — one porting question: owner-only file-backed OAuth persistence with strict validation, cross-instance write serialization, and detached copies.
- `references/search-provider.md` — one porting question: fixed-endpoint OAuth search with secret-free record-before-dispatch, abortable auth, JWT-derived account id, and citeable source normalization.
- `references/search-config-overlay.md` — one porting question: two-layer defaulting of standalone-search knobs from one constant source with parse-time vocabulary validation.
- `references/tool-policy.md` — one porting question: live settings-backed image/Responses/model-catalog policy with migration and cross-provider execution gates.
- `references/image-client.md` — one porting question: generation/edit endpoint selection, OAuth/account headers, cancellation, and fail-closed image-response decoding.
- `references/imagegen-workspace-refs.md` — one porting question: bounded, content-classified workspace paths converted to ordered provider data URLs.
- `references/imagegen-conversation-refs.md` — one porting question: recursive recent conversation attachment selection with exact cardinality and stable order.
- `references/imagegen-tool-boundary.md` — one porting question: policy/capability gates, attachment persistence, and best-effort write-intent publication.
- `references/image-media-type.md` — one porting question: shared magic-byte classification for PNG/JPEG/GIF/WebP image inputs.
- `references/read-image-http-input.md` — one porting question: local read_image delegation plus bounded HTTP(S) loading and attachment projection.
- `references/read-image-sync-lifecycle.md` — one porting question: per-agent enhanced read_image shadow synchronization and teardown.
- `references/responses-transport-choice.md` — one porting question: per-call SSE versus cached WebSocket transport from live preferences, with refcounted compaction marks kept off the continuation chain.
- `references/compaction-marker-codec.md` — one porting question: versioned text-checkpoint framing that carries provider-native output losslessly both directions.
- `references/compaction-sse-parse.md` — one porting question: strict V2 compaction SSE parsing into retained history plus exactly one compaction item.
- `references/compaction-retry-ladder.md` — one porting question: abort-aware retries honoring server Retry-After hints under a hard two-attempt cap.
- `references/responses-usage-projection.md` — one porting question: fail-closed-to-zero subscription usage projection with structural zero costs.
- `references/native-compaction-request.md` — one porting question: V2 compaction request shaping/auth headers with a guaranteed standard-stream fallback.
- `references/doctor-diagnostics.md` — one porting question: secret-free metadata-only credential states, conflict asserts, and non-mutating repair hints.
- `references/compatibility-contract.md` — one porting question: exact-version compatibility evaluation with first-class unknown states and a bounded manifest search.
- `references/service-facade.md` — one porting question: singleton credentials plus live policy behind a provider-owned context service that any number of optional front doors share without changing host defaults.
- `references/public-http-guard.md` — one porting question: resolve-check-pin public HTTP fetching where every DNS answer must be public, redirects are freshly rechecked, and bodies obey declared and streamed byte ceilings.
- `references/search-event-ledger.md` — one porting question: registering a plugin-owned secret-free session event in a guarded host vocabulary and appending the exact request strictly before dispatch.
- `references/cli-doctor-json.md` — one porting question: versioned single-line doctor/status JSON documents that structurally omit secrets, strict flag matrices, and exit codes encoding actionable failure.
- `references/adapter-replay-models.md` — one porting question: read-time identity-preserving replay-state lifting, advertise-versus-resolve model visibility splitting, and a bounded extended retry policy for proxy-blip-prone traffic.
- `references/oauth-bearer-provider-auth.md` — one porting question: projecting a subscription OAuth token into the generic adapter's apiKey slot with zero environment discovery and fail-the-request-on-empty semantics.
- `references/single-profile-adapter-factory.md` — one porting question: assembling one provider profile through layered wrappers and late-bound closures without forking the generic adapter.
- `references/detached-model-catalog-projection.md` — one porting question: exposing the full provider catalog as fresh minimal copies that policy, settings, and UI can never mutate through.
- `references/client-slot-injection.md` — one porting question: a browser plugin entry that mounts settings/tool-view/composer surfaces into host slots with injectable dependencies and effect-owned resource reclamation.
- `references/settings-account-lifecycle.md` — one porting question: a seven-state OAuth account page with popup-before-await sign-in, state-specific poll intervals, and named untrusted-origin remediation.
- `references/client-json-request.md` — one porting question: one same-origin JSON route client with conditional serialization, server-message-first errors, and a single typed error.
- `references/quota-indicator-projection.md` — one porting question: fail-soft whole-payload usage validation, exact model-to-bucket selection, threshold colors, and eligibility-gated abort-clean polling.
- `references/fast-mode-toggle-contract.md` — one porting question: server-authoritative per-session toggling over GET/POST routes with prior-state restore and identity-checked controller ownership.
- `references/imagegen-tool-view.md` — one porting question: defensive tool-result parsing (output_path/output_error markers), injectable promise-cached image loading, and degrade-to-raw presentation.
- `references/tui-login-controller.md` — one porting question: a background browser login that returns control immediately, with challenge settlement, logout-cancel versus teardown-dispose asymmetry, and never-resolving abort-wait prompts.
- `references/tui-headless-browser-launch.md` — one porting question: cross-platform HTTPS-only argv-element browser spawning with honest headless degradation and launch outcome as data.
- `references/tui-command-tree-completion.md` — one porting question: capability-optional dual registration of executable commands and bilingual canonical-path completion trees sharing only the root word.
- `references/tui-command-handler-contract.md` — one porting question: total argv grammar with HELP-as-failure arity guards, echo-after-write projections, NaN-tolerant rendering, and redaction-plus-truncation error results.
- `references/binary-local-write-contract.md` — one porting question: fail-closed sandbox ladders checked before locking, strict replaceIfVersion/createIfAbsent intent gates, and capability-probing non-local dispatch.
- `references/binary-atomic-publish-lock.md` — one porting question: same-directory exclusive-temp publication committed by link-or-rename under tail-chained per-path in-process locks.
- `references/image-vision-gate.md` — one porting question: one module-level gate both image tools share, resolving the current conversation model route and refusing unknown or non-image modalities before any request.
- `references/plugin-assembly-order.md` — one porting question: conflict-assert-before-register wiring with an ascending inject ladder and closure-based late binding of request-time state.
- `references/noop-invariant-companion.md` — one porting question: registering an explicit empty invariant installer whose comment names which owning operation validates each risk.
- `references/settings-route-gates.md` — one porting question: browser-writable Fast Mode and preference-patch routes failing closed through one bounded-body kernel with exact-shape validators and secret-free refusals.
- `references/version-injection-bridge.md` — one porting question: embedding the package version at runtime through an ambient-declare bridge defined identically by every build/test surface from one package.json read.
- `references/profile-composition-patch.md` — one porting question: shipping composition defaults as repo-owned patch rows that saved user settings override, with a dependency-scoped optional terminal door.
- `references/release-provenance-gate.md` — one porting question: gating npm releases on tag-version parity before install and publishing keylessly via OIDC provenance.

## Capsule map
**OAuth and Web route control plane**
- **Provider auth adapter** — `auth-provider-adapter`: bind one provider-native OAuth flow to one credential store and expose only authenticated/expiry status.
- **Browser challenge lifecycle** — `web-auth-challenge`: single-flight login, HTTPS-only challenge validation, waiter fan-out, and timeout settlement.
- **Cancellation and teardown** — `web-auth-cancellation`: abort, reject waiters, await quiescence, then delete on sign-out while preserving credentials on disposal.
- **Status recovery** — `auth-status-recovery`: distinguish signed-out, reauth-required, transient quota error, and browser-flow error without masking valid storage.
- **Trusted request gate** — `trusted-origin-gate`: loopback/peer/origin metadata ladder plus exact persistent remote-origin trust.
- **Trusted origin store** — `trusted-origin-store`: owner-only sidecar of normalized exact origins; strict version/mode/field validation, lock-serialized read-modify-write, atomic 0600 writes, detached sorted results.
- **Auth route contract** — `auth-route-contract`: exact paths/methods, authorize-before-side-effect JSON handlers, and effect-owned cleanup.
- **CLI auth modes** — `cli-auth-device-code`: browser/device-code prompt selection, event rendering, option rejection, and signal-safe cleanup.

**Provider state and transport**
- **Per-session state** — `fast-mode-registry`: positive-only `Map<string, true>` with validated opaque session ids, bounded capacity, LRU eviction with touch-on-read retention, and a provider decorator that injects `service_tier: 'priority'` by merge without clobbering an existing `onPayload` replacement.
- **Quota/usage parsing** — `usage-quota-parsing`: fail-closed `parseOpenAICodexUsage` projecting rate-limit buckets, credits, and spend-control into a secret-free object, plus a fixed reauth error.
- **Owner-only credential store** — `credential-store`: strict versioned document validation, POSIX mode gate, file-lock-serialized atomic writes, detached reads, and foreign-provider refusal.
- **Standalone web-search provider** — `search-provider`: fixed endpoint, JWT-derived account id, secret-free request record before dispatch, abortable auth, and deduplicated citeable sources.
- **Search config overlay** — `search-config-overlay`: schema-default plus `??`-ladder defaulting of model/mode/context/budget from one constant source with closed vocabularies validated at parse time.
- **Live settings-backed policy** — `tool-policy`: detached live projections, Responses migration, provider-ordered model intersection, watcher discipline, and execution-time cross-provider imagegen gate.
- **Adapter assembly policy** — `adapter-replay-models`: read-time identity-preserving legacy replay-state lift inside `stream`, `listModels` advertisement filter that leaves hidden models resolvable, and a bounded 5-attempt/1s–30s retry policy sized for proxy blips.
- **OAuth bearer auth plane** — `oauth-bearer-provider-auth`: decorate-then-override resolver projecting the subscription token into apiKey shape, never discovering environment credentials, failing the request on empty.
- **Single-profile factory** — `single-profile-adapter-factory`: one-entry profiles map layering transport wrap → OAuth/fast-mode decoration → vendored provider through three zero-arg closures; two token paths over one store.
- **Detached catalog projection** — `detached-model-catalog-projection`: call-fresh `{id,name}`-only catalog copies seeding policy intersection and settings snapshots while advertisement narrows independently.

**Image tooling plane**
- **Codex image client** — `image-client`: signal-first generation/edit endpoint selection, OAuth/account headers, bounded provider diagnostics, and base64 image decoding.
- **Workspace image references** — `imagegen-workspace-refs`: active-cwd resolution, regular-file/byte/media gates, attachment validation, observation, and ordered data URLs.
- **Conversation image references** — `imagegen-conversation-refs`: recursive attachment flattening, newest-suffix selection, exact cardinality, and store-mediated reads.
- **Imagegen tool boundary** — `imagegen-tool-boundary`: policy/capability gates, PNG attachment durability, write-intent publication, and bounded write errors.
- **Image media classifier** — `image-media-type`: side-effect-free PNG/JPEG/GIF/WebP magic-byte classification shared by image tools.
- **HTTP read_image enhancement** — `read-image-http-input`: exact-one-source dispatch, local delegation, public HTTP byte/media gates, and attachment projection.
- **Read-image shadow lifecycle** — `read-image-sync-lifecycle`: identity-keyed per-agent registration, event resynchronization, re-entrancy suppression, and effect cleanup.

**Responses runtime and diagnostics plane**
- **Transport choice** — `responses-transport-choice`: per-call preference read picks `websocket-cached` or `sse`; refcounted purpose marks force plain SSE for housekeeping streams without retaining plugin continuation state.
- **Compaction marker codec** — `compaction-marker-codec`: validate-on-write/read versioned tags frame opaque native output as assistant text and expand back through whole-message replacement.
- **Compaction SSE parse** — `compaction-sse-parse`: boundary-safe buffering splitter collecting exactly one compaction item behind a required terminal event with bounded failure details.
- **Compaction retry ladder** — `compaction-retry-ladder`: hint-first delays (retry-after-ms/seconds/date), 429/5xx-only retry set, abort-racing waits, attempts clamped to two, 1000-char error bodies.
- **Usage projection** — `responses-usage-projection`: guarded numeric reads floor input below cached/cache-write tokens and keep every cost component structurally zero.
- **Native compaction request** — `native-compaction-request`: strip-last/expand-markers/retained-filter/trigger-item body composition, JWT-derived account header, session/thread/request-id plus routing headers, onResponse status observation, and standard-stream fallback on any non-abort failure.
- **Doctor diagnostics** — `doctor-diagnostics`: five-state lstat credential ladder, embedded-secret report discipline, fail-before-registry conflict assert, advisory-only hints.
- **Compatibility contract** — `compatibility-contract`: exact-equality package checks, incompatible>unknown>compatible aggregation, strict node range parsing, injectable version-reader seam, depth-bounded manifest walk.

**Service facade, public network, event ledger, and CLI planes**
- **Provider service facade** — `service-facade`: one credentials store + one live policy behind a typed context slot; pure delegation so optional front doors share state without host-default changes; quota reads never issue model requests.
- **Public HTTP guard** — `public-http-guard`: every resolved address must be public, checked addresses are pinned into sockets, redirects re-resolve and re-validate up to five hops, and bodies obey declared plus streamed ceilings under a per-hop timeout.
- **Search event ledger** — `search-event-ledger`: guarded registration of a plugin-owned session event into an extensible-only vocabulary, with record-before-dispatch appends to the initiating agent's session and no log outside agent turns.
- **CLI doctor JSON** — `cli-doctor-json`: schemaVersion-stamped single-line documents, structural omission of credential paths/tokens, strict flag matrix, redacted stderr, exit codes for fatal states only.

**Client UI plane**
- **Slot-injected browser entry** — `client-slot-injection`: one `name`/`inject`/`apply` triad registering four surfaces; per-session promise-cached object URLs revoked via paired effects; locale dictionaries type-checked for en/zh parity.
- **Settings account lifecycle** — `settings-account-lifecycle`: closed seven-state account union, popup opened before the first await, 1 s signing-in / 60 s signed-in poll ladder, trust-origin remediation card with clipboard copy.
- **Client JSON route client** — `client-json-request`: same-origin credentials, body-conditional content-type, lenient parse, `AccountRequestError` with server-message extraction; schema trust stays at consumers.
- **Quota indicator projection** — `quota-indicator-projection`: all-or-nothing payload validation, exact Spark bucket selection without fallback, clamped percent with green/yellow/orange/red thresholds, null-render on anything unusable.
- **Fast Mode session toggle** — `fast-mode-toggle-contract`: optimistic busy-ness only, server response authoritative, prior state restored on failure, controllerRef identity checks across GET/POST/unmount races.
- **Imagegen tool view** — `imagegen-tool-view`: first-image-wins parsing, output_path/output_error marker scan, prompt-summary fallbacks, portal preview with Escape/focus restoration, saved-path openFile row.

**Terminal command and binary publication planes**
- **TUI login controller** — `tui-login-controller`: single-flight background login whose fast challenge promise is settled by the first auth_url event; select prompts answered synchronously, others wait on abort only; logout cancels+drains+deletes while dispose cancels+drains and preserves credentials.
- **Headless browser launch** — `tui-headless-browser-launch`: URL-parsed HTTPS refusal, fixed per-platform command table as argv elements, detached fire-and-forget spawn, linux DISPLAY/WAYLAND probe returning false so the caller embeds the manual-open URL.
- **Command tree completion** — `tui-command-tree-completion`: independent commands/tuiCommandTrees injections, total canonical-path responder over three depths returning [] otherwise, structurally paired en/zh descriptions, openAICodexTui marker present only with a tree runtime.
- **Codex command handler** — `tui-command-handler-contract`: tokenized argv defaulting to status, strict arity guards returning HELP, post-write config echo, name??id usage projection with unlimited/balance/'available' credits fallback, safeMessage twin adding slice(0,1000).
- **Local byte-write contract** — `binary-local-write-contract`: sandbox ladder (undefined→passthrough, missing policy fail-closed, read-only/danger modes, workspace-write fresh resolve + contains), intent gates inside the lock, lstat-preserved mode, create/update outcome from re-stat.
- **Atomic publish + promise lock** — `binary-atomic-publish-lock`: pid+UUID exclusive temp in the destination directory, write/fsync/chmod/close, abort re-check before commit, link-vs-rename by intent with EEXIST→FS_NOT_OBSERVED, finally cleanup, self-cleaning tail-chained lock map.

**Assembly, vision gate, and settings route planes**
- **Shared image vision gate** — `image-vision-gate`: header-config-first model-route resolution, fail-closed modality check (`undefined` modalities ≠ image-capable), signal-forwarded capability lookup, one error grammar for both consuming tools.
- **Composite plugin assembly** — `plugin-assembly-order`: search-event vocabulary first, conflict assert before any registry mutation, provide-one-slot composition, ascending per-surface inject ladders, zero-arg closures keeping snapshots/attachments request-time fresh.
- **No-op invariant companion** — `noop-invariant-companion`: second plugin entry registering an empty installer under the package id with the ownership rationale in source; separate build entry keeps the declaration independently loadable.
- **Settings route gates** — `settings-route-gates`: 4096-byte declared+streamed body ceiling with running-total enforcement, strict digits-only content-length, exact-two-key toggle payloads, allow-listed patch validators naming rejected keys, RangeError→413 mapping, secret-free 403 bodies, disable-by-deletion.

**Build, composition, and release plumbing planes**
- **Version injection bridge** — `version-injection-bridge`: ambient declare bridged to an export, defined identically by tsdown ESM/CJS and vitest from one package.json read; any surface missing its define fails loudly at import.
- **Profile composition patch** — `profile-composition-patch`: repo-owned patch rows defaulting agent model and search provider plus an insert block adding the bundle and an inject-scoped dormant terminal door; saved user settings still win.
- **Release provenance gate** — `release-provenance-gate`: v*-tag workflow serializing releases under one concurrency group, checking tag↔package.json parity before install, publishing keylessly under contents:read + id-token:write only.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question against project `dsh-codex`. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf. Candidate seams for future passes live in the dsh-codex-work record next-pass targets.

## Provenance
dsh-codex (Apache-2.0), `main@e3e54e206f7c829503c7e6eed378643ba0416792`; Codebase Memory project `dsh-codex` (FULL, 934 nodes / 2717 edges, ready, root/HEAD match, live coverage generation 2026-08-24T16:11:14Z; one parse-partial file `tests/auth-routes.spec.ts:40`, zero skipped files, `.git` deliberately excluded).

## Full view (memory graph)
Revalidate `dsh-codex` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and the parse-partial test caveat; source and direct tests decide shipped claims.

## Boundaries
Adopt the provider adapter, single-flight HTTPS challenge, cancel→drain→delete lifecycle, quota-separated status recovery, fail-closed exact-origin gate, exact route/effect composition, CLI auth-mode selection, bounded positive-only Fast Mode registry, secret-free quota projection, owner-only credential store, abortable search, and live settings policy. Adapt provider factories, OAuth event/prompt vocabulary, route framework, origin persistence, endpoint/header values, and Codex-specific setting names. Omit provider-native PKCE/token exchange internals (delegated to pi-ai here), Codex route constants, and non-portable first-party endpoint/dependency details.
