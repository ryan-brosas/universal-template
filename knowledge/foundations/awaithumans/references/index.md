<!-- Preserved verbatim from the pre-foundation-skill-v1 loader. Its `references/` pointers are historical loader-relative paths; use the linked inventory below from this location. -->

# AwaitHumans Foundation: Human-in-the-Loop Async Task Platform

## Use this for
Use when building a human-in-the-loop task platform or SDK: a reconnecting long-poll client loop over gateway-safe windows, dynamic JSON schema form inference, single-use signed magic link action tokens, HKDF-derived key separation for tokens/secrets, task lifecycle state machines with terminal guards, and retryable webhook dispatch. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/await-human-poll-loop.md` — reconnecting long-poll client loop over gateway-safe windows and typed terminal exception mapping.
- `references/dev-discovery-file.md` — local development server discovery file for zero-config CLI and SDK testing.
- `references/hkdf-key-separation.md` — HKDF key derivation separating session encryption, magic link signing, and webhook HMAC keys.
- `references/idempotency-contract.md` — idempotency key caching, payload hashing, and concurrent task dedup.
- `references/magic-link-action-tokens.md` — stateless single-use signed action tokens for email/SMS human response submission.
- `references/schema-form-inference.md` — JSON Schema and Pydantic response schema translation into dynamic UI form fields.
- `references/session-and-handoff-auth.md` — session authentication, API key verification, and human handoff authorization.
- `references/task-terminal-guards.md` — task state machine enforcing valid transitions and terminal state immutability.
- `references/webhook-retry-queue.md` — exponential backoff webhook dispatch queue with status verification and signature headers.
- `references/verifier-loop.md` — verifier loop: automated response validation and rejection retry ladder.
- `references/temporal-signal-adapter.md` — Temporal signal adapter: workflow blocking and external signal unblocking.
- `references/five-fragment-masking.md` — five-fragment masking: PII and sensitive data masking for human tasks.
- `references/langgraph-interrupt-adapter.md` — LangGraph interrupt adapter: node-level interruption and resumption envelope.
- `references/typed-error-parity.md` — typed error parity: cross-language SDK exception parity and wire envelopes.
- `references/tz-aware-runtime-patch.md` — timezone-aware runtime patch: UTC normalization across temporal calculations.
- `references/routing-and-assignment.md` — routing and assignment: skill-based and team-based human task assignment.
- `references/notify-route-grammar.md` — notify route grammar: multi-channel notification templating and delivery dispatch.
- `references/ts-sdk-wire-boundary.md` — TS-SDK wire boundary: single-module camelCase→snake_case translation so Pydantic `extra="ignore"` can't silently drop caller config.
- `references/ts-sdk-idempotency-key.md` — canonical-JSON idempotency key: sorted-object-keys stringify + truncated SHA-256 with array-order preservation.
- `references/durable-terminal-shortcircuit.md` — terminal-echo idempotency short-circuit: create-before-interrupt plus cached-response return when the webhook already fired (#72).
- `references/twin-scheduler-loops.md` — twin scheduler loops: crash-proof asyncio sweeps with fresh-session-per-tick and sleep-outside-try.
- `references/rate-limiter-doctrine.md` — sliding-window rate limiter doctrine: reject-without-bump, success-path reset, and deliberate no-lockout semantics.
- `references/timing-equalized-login.md` — timing-equalized argon2 login: import-time dummy hash burns identical CPU on the unknown-user path.
- `references/versioned-column-encryption.md` — versioned AES-GCM column encryption: TypeDecorator over key_id‖nonce‖ciphertext blobs with loud no-fallback decrypt.
- `references/slack-signature-ladder.md` — Slack signature ladder: v0 HMAC over raw body plus 5-minute staleness window, boolean-not-raise contract.
- `references/slack-coercion-dispatch.md` — Slack view-state coercion: form-definition-driven per-primitive dispatch from Block Kit state to flat typed responses.
- `references/hkdf-handoff-urls.md` — channel-scoped HKDF handoff URLs: pipe-canonical signed URLs that clear the dashboard login wall without becoming a universal login.
- `references/form-field-registry.md` — form field primitive registry: kind-discriminated base, option normalization ladder, and channel degradation conventions.
- `references/review-merge-confidence.md` — review-merge confidence protocol: client-side human-verdict merge with flag surgery and provisional-calibration honesty.
- `references/task-auth-caller-taxonomy.md` — three-caller task authorization: admin/operator/assignee gates over state-stamped claims.
- `references/cross-runtime-sdk-primitives.md` — cross-runtime SDK primitives: typed env shim and timeout-owned fetch wrapper for Node/Bun/Deno/edge.
- `references/langgraph-callback-decoupling.md` — framework-agnostic LangGraph resume handler: injected Command vs static interrupt and mirrored HKDF verification.
- `references/flow-b-extraction-dispatch.md` — Flow B model-then-human extraction: two-flavor provider dispatch (LLM single-call vs OCR+structuring) with local-only execution, strict-off Responses API, forced tool call, and loud ProviderNotSupportedError for typed-but-unimplemented configs.
- `references/slack-interactivity-entry.md` — Slack /interactions webhook: raw-body-twice HMAC, claim-first disambiguation, authorize-before-modal/submission, response_url→postEphemeral ladder, fire-and-forget surface swap under the 3s submission budget.
- `references/slack-auto-link-identity-binding.md` — first-click identity auto-link: conditional UPDATE guarded on `slack_user_id IS NULL`, refuse-not-overwrite, race-convergent by construction (#144).
- `references/bootstrap-token-error-taxonomy.md` — one-shot in-memory bootstrap token (idempotent generate, fail-closed verify, permanent clear) plus the ServiceError class-attribute taxonomy driving ONE exception handler envelope.
- `references/embed-jwt-lifecycle.md` — embed JWT lifecycle: TTL clamp-before-sign, HS256 algorithm-pinning allowlist, typed PyJWT error ladder, sortable 29-char jti.
- `references/origin-allowlist-grammar.md` — iframe-parent origin allowlist: validate-at-parse grammar (no path/trailing-slash/http-except-localhost) and single-leading-label wildcard matching that never matches the apex.
- `references/embed-auth-passthrough-gates.md` — embed bearer middleware: default-None state then four passthrough gates (non-bearer, ah_sk_, non-JWT shape, disabled feature) before verify; only crypto-invalid JWTs get the early 401.
- `references/slack-oauth-install-flow.md` — multi-workspace OAuth install: install-token start gate, single-workspace mode lockout, cookie∧HMAC∧TTL callback triple, single-use state-cookie deletion.
- `references/post-completion-message-update.md` — post-completion chat.update fan-out: snapshot-by-id signature, one signed review URL per task, team-scoped client with no default fallback, swallow-everything error posture.
- `references/handoff-url-builder-expiry.md` — handoff URL builder: params-None-means-unsigned dispatch and expiry derived from the task's own deadline so links die with the task.
- `references/magic-token-single-use-consumption.md` — magic-link token consumption: pre-check + PK-conflict INSERT committed independently so completion failures can't resurrect a burned token.
- `references/notification-failure-audit.md` — notification_failed audit entries: own-commit persistence after the parent transaction closed, loud-swallow, from_status=None as no-transition marker.
- `references/oauth-state-nonce.md` — stateless OAuth state nonce: nonce:ts:hmac base64url shape, decode→constant-time-HMAC→abs-age verify ladder, reused Slack signing secret.
- `references/service-key-hash-at-rest.md` — service keys: SHA-256 hash-only storage, show-once raw keys, same NotFound for miss AND revoked, idempotent revoke, ULID-shaped sortable ids.
- `references/channel-config-boot-validator.md` — boot-time channel config validator: per-channel required-env census emitting ONE consequence-predicting WARNING per half-configured channel, never raising.
- `references/log-secret-scrubber.md` — root-handler log scrubber: pattern list with group-count-keyed replacement styles, msg+args scrubbing before formatting, request-id correlation.
- `references/naive-datetime-utc-boundary.md` — naive-datetime UTC boundary pair: to_utc_unix for epoch crossings and utc_iso Z-suffix serialization wherever SQLite-stripped tzinfo meets a channel.
- `references/admin-gate-dual-credential.md` — require_admin dual credential: constant-time X-Admin-Token/bearer OR operator session, 403-not-503 when both absent.
- `references/secret-lookup-funnel.md` — Settings.get_secret funnel: declared-field-first then os.environ fallback so runtime-named verifier API keys still see .env loading.
- `references/stats-python-aggregation.md` — stats aggregation: window-vs-all-time per-metric semantics, zero-filled day axis, None-not-zero rate/average, documented CTE growth path.
- `references/encrypted-config-list-deferral.md` — encrypted-column list deferral: defer(raiseload=True) so one stale-key row can't 500 the whole listing; single sanctioned decrypt helper.
- `references/email-transport-factory-traps.md` — email transport factory: raise-in-constructor vs swallow-to-None resolver split, port-465 implicit-TLS default, user/username alias, unknown-name error lists valid transports.
- `references/slack-installations-admin-surface.md` — Slack installations admin surface: router-wide require_admin, token-absent public shapes, cached auth.test static-workspace entry, specific SlackApiError catches, FastAPI 204 response_class override.
- `references/sdk-type-contract-plane.md` — SDK type contract plane: TaskStatus 11-member ladder, timeout bounds, AssignTo union vocabulary shared across Python/TS/server/UI.
- `references/managed-client-wire-contract.md` — AwaitVerify managed client: signed-URL fragment uploads with client-side DEK, omit-vs-null wire semantics for no-document tasks, long-poll with +10s client headroom, status-mapped error hints.
- `references/complex-forms-capability-law.md` — Table/Subform complex primitives plus the capability law: any LINK_OUT field falls the WHOLE form back in that channel; recursive unsupported_fields walk; exhaustive kind×channel test.
- `references/nextjs-static-export-shim.md` — Next.js static-export URL shim: try `<path>.html` first for extensionless clean URLs (S_ISREG-checked) inside a synchronous lookup_path override.
- `references/verifier-config-error-taxonomy.md` — verifier config helpers & error taxonomy: thin config factories executed server-side; what→why→fix→docs VerifyError family over the ServiceError base.
- `references/slack-message-ledger.md` — Slack message ledger: record-then-update DAL with deliberately NO unique constraint (duplicate row = idempotent double update), best-effort inserts.
- `references/email-palette-inline-css.md` — email palette: inline-CSS-only constraint (clients strip style blocks) and convention-synced brand tokens duplicated from dashboard theme on purpose.
- `references/cli-command-surface.md` — CLI command surface: one module per operator command as logic-free shells over service functions via a shared discovery-resolved session helper.
- `references/server-poll-hold.md` — server-side long-poll hold: fresh-session-per-tick re-reads so parked polls hold zero pool slots, authorize-once snapshot, ≤30 s Query clamp answering timeout with last status and null payload.
- `references/sdk-client-facade.md` — AwaitHumans client facade: arg→env→hosted-default config binding, function-local heavy imports for workflow-sandbox replay, asyncio.run sync bridges, camelCase aliases over one lazy default client.
- `references/partial-idempotency-index.md` — partial UNIQUE index over ACTIVE idempotency keys only: enum-NAME WHERE derived from TERMINAL_STATUSES_SET so concurrent INSERT races lose loudly while app-layer recovery lookup stays deliberately unscoped.
- `references/tz-timestamp-columns.md` — tz timestamp columns: DateTime(timezone=True) declaration law so asyncpg binds tz-aware datetimes, per-field Column instances, metadata-walk completeness test paired with the boot-time ALTER patch.
- `references/ephemeral-sqlite-prod-warning.md` — production SQLite durability warning: operator-acknowledgment env var instead of filesystem heuristics, scheme-or-default detection, single multi-line WARNING record with pinned actionable strings.
- `references/first-run-setup-gating.md` — first-run setup gating: public-by-design /api/setup/* route self-gating through per-IP rate limit, DB user-count re-check that self-heals the bootstrap flag, fail-closed one-shot token verify, and inline session cookie.
- `references/optimistic-response-redaction.md` — optimistic response redaction: pure client overlay pre-playing the server's eventual row shape to close the submit-ACK→callback privacy window, DeliveredPlaceholder priority branch, idempotent non-null-skip server twin.
- `references/form-response-value-builder.md` — form response value builder: recursive omit-null-on-optional wire shaping so Pydantic defaults apply, required nulls kept loud, empty string/array preserved as meaningful.
- `references/embed-iframe-client-plane.md` — embed iframe client plane: fragment-borne token, one-way source-tagged postMessage keyed to the JWT parent_origin claim, bearer-only same-origin fetch.
- `references/user-directory-write-funnel.md` — user directory write funnel: single service funnel for admin/CLI/setup/task-router writes, app-layer invariants partial indexes can't express, count-based last-active-operator guard.
- `references/form-initial-value-prefill.md` — form initial value + prefill: per-kind default ladder over NON_INPUT_KINDS exclusion and typed prefill precedence so display fields never enter response state.
- `references/boot-url-cors-gatekeepers.md` — boot URL/CORS gatekeepers: refuse-to-start validators closing the allow_credentials-coupling session-ride trap and the PUBLIC_URL path-stack footgun.
- `references/dashboard-data-client.md` — dashboard data client: bundled same-origin vs dev-discovery base resolution with retry-once-after-invalidation, envelope-shaped ApiError ladder, credentials-include.
- `references/audit-trail-append-only.md` — audit trail append-only plane: one row per transition with actor/channel/embed attribution, read gate equals parent-task gate, rows deliberately orphaned on hard delete.
- `references/claim-first-writer-wins.md` — claim first-writer-wins: guarded conditional UPDATE whose WHERE re-encodes unassigned+non-terminal, loser-naming refresh re-read, operator-session-only route shell.
- `references/task-list-serialization-plane.md` — task list serialization: bulk user index vs per-task lookup split by cardinality, list-always-redacts, server-forced non-operator scoping.
- `references/assignee-directory-search-ladder.md` — assignee directory search ladder: one-round-trip email/slack-id/display-name-substring resolution with the pre-provisioning email fallback branch.
- `references/completer-attribution-authorize-first.md` — completer attribution authorize-first: authorize before the verifier runs, server-derived identity triple, terminal-gated webhook/Slack fan-out.
- `references/url-state-filter-roundtrip.md` — URL-as-state operator filters: allowlist read, omit-defaults write, offset snap-back, total-less hasNextPage.
- `references/completion-bookkeeping-latches.md` — completion bookkeeping latches: completed_at on COMPLETED only, redaction-gated derived audit fields, authoritative channel kwarg precedence.
- `references/alembic-orphan-recovery-migration.md` — alembic orphan-recovery migration: stamp-back plus an idempotent IF EXISTS cleanup head when upstream deletes shipped migration files.
- `references/filter-affordances-server-mirror.md` — filter affordances as a server-semantics mirror: mutual exclusion on turn-on, empty-intersection disabled search, operator-gated Mine, context-hidden Unassigned toggle.
- `references/slack-modal-forward-rendering.md` — Slack modal forward rendering: form-definition-driven view assembly, private_metadata task identity, authorize-before-coercion consumer, redact_payload preview suppression.
- `references/slack-element-degradation-ladder.md` — Slack element degradation ladder: kind×cardinality element selection, form-derived block_id/action_id addressing on build AND parse sides, loud unrenderable backstop.
- `references/slack-card-button-algebra.md` — Slack card button algebra: claim-XOR-open primaries, always-present dashboard link, total-function terminal swap that strips every interaction.
- `references/email-notification-button-algebra.md` — email notification button algebra: magic-link buttons only for exactly-one-small-input forms, recipient-baked tokens, deadline-bound handoff URLs, always-present Open-task CTA.

## Capsule map
- **Client polling, discovery & SDK facade** — `references/await-human-poll-loop.md`, `references/server-poll-hold.md`, `references/dev-discovery-file.md`, `references/typed-error-parity.md`, `references/cross-runtime-sdk-primitives.md`, `references/sdk-client-facade.md`: long-poll client loop plus its server-side hold twin, dev discovery file, typed error parity, cross-runtime env/fetch primitives, multi-primitive client facade.
- **Security & tokens** — `references/hkdf-key-separation.md`, `references/magic-link-action-tokens.md`, `references/session-and-handoff-auth.md`, `references/five-fragment-masking.md`, `references/hkdf-handoff-urls.md`, `references/versioned-column-encryption.md`, `references/timing-equalized-login.md`, `references/rate-limiter-doctrine.md`, `references/task-auth-caller-taxonomy.md`, `references/slack-signature-ladder.md`: HKDF key derivation, magic-link action tokens, session auth, five-fragment masking, signed handoff URLs, column encryption, timing equalization, rate limiting, task authorization, Slack signature verification.
- **Task lifecycle & forms** — `references/task-terminal-guards.md`, `references/idempotency-contract.md`, `references/ts-sdk-idempotency-key.md`, `references/durable-terminal-shortcircuit.md`, `references/schema-form-inference.md`, `references/form-field-registry.md`, `references/webhook-retry-queue.md`, `references/twin-scheduler-loops.md`, `references/verifier-loop.md`, `references/review-merge-confidence.md`, `references/temporal-signal-adapter.md`, `references/langgraph-interrupt-adapter.md`, `references/langgraph-callback-decoupling.md`, `references/tz-aware-runtime-patch.md`, `references/routing-and-assignment.md`, `references/notify-route-grammar.md`, `references/slack-coercion-dispatch.md`, `references/ts-sdk-wire-boundary.md`, `references/partial-idempotency-index.md`, `references/optimistic-response-redaction.md`, `references/form-response-value-builder.md`, `references/form-initial-value-prefill.md`, `references/claim-first-writer-wins.md`: terminal state guards, idempotency keys (server + canonical-JSON derivation + partial ACTIVE-only unique index), terminal short-circuit, optimistic redaction overlay, response value builder, initial-value/prefill derivation, guarded-UPDATE claim race, schema form inference, field primitives, webhook retry queue, scheduler loops, verifier loop, review merge, framework adapters (direct/temporal/langgraph + callback decoupling), routing, notifications, Block Kit coercion, and the wire translation boundary.
- **Operator queue, filters & completion plane** — `references/task-list-serialization-plane.md`, `references/assignee-directory-search-ladder.md`, `references/completer-attribution-authorize-first.md`, `references/url-state-filter-roundtrip.md`, `references/completion-bookkeeping-latches.md`, `references/filter-affordances-server-mirror.md`: bulk-index list serialization with forced scoping and always-redact lists, broad assignee resolution with the pre-provisioning email branch, server-derived completer identity behind authorize-before-verifier, URL-as-state operator filters with total-less pagination, outcome-keyed completion latches, and filter UI that mirrors the server's filter algebra.

- **Slack Block Kit surface plane** — `references/slack-modal-forward-rendering.md`, `references/slack-element-degradation-ladder.md`, `references/slack-card-button-algebra.md`: the forward (build) direction of the Block Kit contract — definition-driven modals riding task identity in private_metadata, the kind×cardinality element ladder over form-derived addressing keys shared with coercion, and per-state card button algebras whose terminal swaps strip every interaction.
- **Email notification surface** — `references/email-notification-button-algebra.md`: the email-side twin — single-small-input magic-link gate with recipient-baked tokens and deadline-bound handoff URLs.
- **Server surfaces & platform** — `references/slack-interactivity-entry.md`, `references/slack-auto-link-identity-binding.md`, `references/bootstrap-token-error-taxonomy.md`, `references/user-directory-write-funnel.md`, `references/first-run-setup-gating.md`: the /interactions webhook (raw-body HMAC, claim races, 3s budget), first-click identity binding with refuse-not-overwrite conditional updates, one-shot bootstrap tokens, the self-gating first-run setup route, the single-funnel user directory with its last-active-operator guard, and the ServiceError→single-handler envelope.
- **Extraction & verification** — `references/flow-b-extraction-dispatch.md`, `references/verifier-loop.md`, `references/verifier-config-error-taxonomy.md`: Flow B runs every model call on the caller's machine (LLM single-call vs OCR+structuring flavors) while the server-side verifier loop re-checks human answers; thin config factories and the what→why→fix→docs error family.
- **Embed & service-key auth** — `references/embed-jwt-lifecycle.md`, `references/origin-allowlist-grammar.md`, `references/embed-auth-passthrough-gates.md`, `references/embed-iframe-client-plane.md`, `references/service-key-hash-at-rest.md`, `references/admin-gate-dual-credential.md`, `references/secret-lookup-funnel.md`: embed JWT sign/verify with alg-pinning, wildcard origin grammar, bearer passthrough gates, the iframe client half (fragment token + claim-keyed postMessage), hash-at-rest machine keys, dual-credential admin dependency, and the single secret-lookup funnel.
- **Slack workspace lifecycle** — `references/slack-oauth-install-flow.md`, `references/oauth-state-nonce.md`, `references/post-completion-message-update.md`, `references/handoff-url-builder-expiry.md`, `references/slack-message-ledger.md`, `references/slack-installations-admin-surface.md`: install flow with state triple, terminal message updates, deadline-bound handoff URLs, message ledger without uniqueness, and the token-absent admin CRUD surface.
- **Ops & platform hygiene** — `references/channel-config-boot-validator.md`, `references/ephemeral-sqlite-prod-warning.md`, `references/tz-timestamp-columns.md`, `references/log-secret-scrubber.md`, `references/notification-failure-audit.md`, `references/naive-datetime-utc-boundary.md`, `references/stats-python-aggregation.md`, `references/email-transport-factory-traps.md`, `references/encrypted-config-list-deferral.md`, `references/nextjs-static-export-shim.md`, `references/cli-command-surface.md`, `references/magic-token-single-use-consumption.md`, `references/boot-url-cors-gatekeepers.md`, `references/audit-trail-append-only.md`, `references/alembic-orphan-recovery-migration.md`: boot-time config census, handler-level secret scrubbing, own-commit failure audits, the append-only audit trail with its parent-gated read surface, UTC boundary helpers, python-side stats, transport factory traps, encrypted-list deferral, static-export URL shim, thin CLI shells, replay-proof token consumption, the production-SQLite durability warning, the refuse-to-start URL/CORS validator pair, and deleted-upstream-migration recovery via stamp-back plus an idempotent cleanup head.
- **Type & wire contracts** — `references/sdk-type-contract-plane.md`, `references/managed-client-wire-contract.md`, `references/complex-forms-capability-law.md`, `references/email-palette-inline-css.md`, `references/dashboard-data-client.md`: TaskStatus/AssignTo/VerifierConfig vocabulary, signed-URL upload wire semantics with omit-vs-null discipline, Table/Subform + capability link-out law, inline-CSS email constraints, and the operator-dashboard same-origin fetch client.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
awaithumans (Apache-2.0) `main@bc05b8e7`; Codebase Memory project `mnt-hdd-utopia-inspo-awaithumans` (registered root `$REFERENCE_ROOT/awaithumans`, live symlink into `inspo/agents/awaithumans`). Pass 5 (agents-small dedicated lane) added the embed/auth, Slack-workspace-lifecycle, ops-hygiene, and wire-contract planes. Pass 7 (miner-awaithumans lane) wired the pass-6 poll-hold/client-facade/partial-idempotency capsules into this loader and added the tz-column-declaration, ephemeral-SQLite-warning, setup-gating, optimistic-redaction, and response-value-builder planes — all at this same pin. Pass 8 (same lane) wrote embed-iframe-client-plane, user-directory-write-funnel, and form-initial-value-prefill plus key-cache/redaction-parity refactors; Pass 9 (2026-08-26) wired those three into this loader/map and added boot-url-cors-gatekeepers, dashboard-data-client, audit-trail-append-only, and claim-first-writer-wins — all at this same pin; work record `$REFERENCE_ROOT/.skill-mining-work/awaithumans/{state,research,verification}.md` is authoritative from Pass 6 on. Passes 10–14 authored eleven further capsules (operator queue / URL-state / completion-bookkeeping plane incl. the alembic orphan-recovery head, filter-bar server mirror, the Slack Block Kit forward trio, and the email button algebra) plus three refactors and a leaf-wide graph-project-id repair — but those leaf writes were silently LOST; Pass 16 (2026-08-26, miner-awaithumans recovery lane) re-delivered and wired all of them from freshly executed evidence chains at this same pin.

## Full view (memory graph)
Revalidate before porting: project `mnt-hdd-utopia-inspo-awaithumans`, run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`.

## Boundaries
Adopt the long-poll loop, magic link action tokens, HKDF key derivation, idempotency contract, terminal guards, the Flow B local-only extraction dispatch, the refuse-not-overwrite identity binding, and the embed/OAuth security gates; adapt storage adapters and notification providers; omit custom UI views and deployment infrastructure. Vendor extraction/OCR clients (`providers/*`) are thin SDK call wrappers around the contracts captured in flow-b-extraction-dispatch — porting them means re-deriving vendor signatures, not mining more invariants here. CLI commands (`cli/*`) are logic-free shells over service capsules; email template internals beyond palette constraints are product chrome.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`admin-gate-dual-credential.md`](./admin-gate-dual-credential.md)
- [`alembic-orphan-recovery-migration.md`](./alembic-orphan-recovery-migration.md)
- [`assignee-directory-search-ladder.md`](./assignee-directory-search-ladder.md)
- [`audit-trail-append-only.md`](./audit-trail-append-only.md)
- [`await-human-poll-loop.md`](./await-human-poll-loop.md)
- [`boot-url-cors-gatekeepers.md`](./boot-url-cors-gatekeepers.md)
- [`bootstrap-token-error-taxonomy.md`](./bootstrap-token-error-taxonomy.md)
- [`channel-config-boot-validator.md`](./channel-config-boot-validator.md)
- [`claim-first-writer-wins.md`](./claim-first-writer-wins.md)
- [`cli-command-surface.md`](./cli-command-surface.md)
- [`completer-attribution-authorize-first.md`](./completer-attribution-authorize-first.md)
- [`completion-bookkeeping-latches.md`](./completion-bookkeeping-latches.md)
- [`complex-forms-capability-law.md`](./complex-forms-capability-law.md)
- [`cross-runtime-sdk-primitives.md`](./cross-runtime-sdk-primitives.md)
- [`dashboard-data-client.md`](./dashboard-data-client.md)
- [`dev-discovery-file.md`](./dev-discovery-file.md)
- [`durable-terminal-shortcircuit.md`](./durable-terminal-shortcircuit.md)
- [`email-notification-button-algebra.md`](./email-notification-button-algebra.md)
- [`email-palette-inline-css.md`](./email-palette-inline-css.md)
- [`email-transport-factory-traps.md`](./email-transport-factory-traps.md)
- [`embed-auth-passthrough-gates.md`](./embed-auth-passthrough-gates.md)
- [`embed-iframe-client-plane.md`](./embed-iframe-client-plane.md)
- [`embed-jwt-lifecycle.md`](./embed-jwt-lifecycle.md)
- [`encrypted-config-list-deferral.md`](./encrypted-config-list-deferral.md)
- [`ephemeral-sqlite-prod-warning.md`](./ephemeral-sqlite-prod-warning.md)
- [`filter-affordances-server-mirror.md`](./filter-affordances-server-mirror.md)
- [`first-run-setup-gating.md`](./first-run-setup-gating.md)
- [`five-fragment-masking.md`](./five-fragment-masking.md)
- [`flow-b-extraction-dispatch.md`](./flow-b-extraction-dispatch.md)
- [`form-field-registry.md`](./form-field-registry.md)
- [`form-initial-value-prefill.md`](./form-initial-value-prefill.md)
- [`form-response-value-builder.md`](./form-response-value-builder.md)
- [`handoff-url-builder-expiry.md`](./handoff-url-builder-expiry.md)
- [`hkdf-handoff-urls.md`](./hkdf-handoff-urls.md)
- [`hkdf-key-separation.md`](./hkdf-key-separation.md)
- [`idempotency-contract.md`](./idempotency-contract.md)
- [`langgraph-callback-decoupling.md`](./langgraph-callback-decoupling.md)
- [`langgraph-interrupt-adapter.md`](./langgraph-interrupt-adapter.md)
- [`log-secret-scrubber.md`](./log-secret-scrubber.md)
- [`magic-link-action-tokens.md`](./magic-link-action-tokens.md)
- [`magic-token-single-use-consumption.md`](./magic-token-single-use-consumption.md)
- [`managed-client-wire-contract.md`](./managed-client-wire-contract.md)
- [`naive-datetime-utc-boundary.md`](./naive-datetime-utc-boundary.md)
- [`nextjs-static-export-shim.md`](./nextjs-static-export-shim.md)
- [`notification-failure-audit.md`](./notification-failure-audit.md)
- [`notify-route-grammar.md`](./notify-route-grammar.md)
- [`oauth-state-nonce.md`](./oauth-state-nonce.md)
- [`optimistic-response-redaction.md`](./optimistic-response-redaction.md)
- [`origin-allowlist-grammar.md`](./origin-allowlist-grammar.md)
- [`partial-idempotency-index.md`](./partial-idempotency-index.md)
- [`post-completion-message-update.md`](./post-completion-message-update.md)
- [`rate-limiter-doctrine.md`](./rate-limiter-doctrine.md)
- [`review-merge-confidence.md`](./review-merge-confidence.md)
- [`routing-and-assignment.md`](./routing-and-assignment.md)
- [`schema-form-inference.md`](./schema-form-inference.md)
- [`sdk-client-facade.md`](./sdk-client-facade.md)
- [`sdk-type-contract-plane.md`](./sdk-type-contract-plane.md)
- [`secret-lookup-funnel.md`](./secret-lookup-funnel.md)
- [`server-poll-hold.md`](./server-poll-hold.md)
- [`service-key-hash-at-rest.md`](./service-key-hash-at-rest.md)
- [`session-and-handoff-auth.md`](./session-and-handoff-auth.md)
- [`slack-auto-link-identity-binding.md`](./slack-auto-link-identity-binding.md)
- [`slack-card-button-algebra.md`](./slack-card-button-algebra.md)
- [`slack-coercion-dispatch.md`](./slack-coercion-dispatch.md)
- [`slack-element-degradation-ladder.md`](./slack-element-degradation-ladder.md)
- [`slack-installations-admin-surface.md`](./slack-installations-admin-surface.md)
- [`slack-interactivity-entry.md`](./slack-interactivity-entry.md)
- [`slack-message-ledger.md`](./slack-message-ledger.md)
- [`slack-modal-forward-rendering.md`](./slack-modal-forward-rendering.md)
- [`slack-oauth-install-flow.md`](./slack-oauth-install-flow.md)
- [`slack-signature-ladder.md`](./slack-signature-ladder.md)
- [`stats-python-aggregation.md`](./stats-python-aggregation.md)
- [`task-auth-caller-taxonomy.md`](./task-auth-caller-taxonomy.md)
- [`task-list-serialization-plane.md`](./task-list-serialization-plane.md)
- [`task-terminal-guards.md`](./task-terminal-guards.md)
- [`temporal-signal-adapter.md`](./temporal-signal-adapter.md)
- [`timing-equalized-login.md`](./timing-equalized-login.md)
- [`ts-sdk-idempotency-key.md`](./ts-sdk-idempotency-key.md)
- [`ts-sdk-wire-boundary.md`](./ts-sdk-wire-boundary.md)
- [`twin-scheduler-loops.md`](./twin-scheduler-loops.md)
- [`typed-error-parity.md`](./typed-error-parity.md)
- [`tz-aware-runtime-patch.md`](./tz-aware-runtime-patch.md)
- [`tz-timestamp-columns.md`](./tz-timestamp-columns.md)
- [`url-state-filter-roundtrip.md`](./url-state-filter-roundtrip.md)
- [`user-directory-write-funnel.md`](./user-directory-write-funnel.md)
- [`verifier-config-error-taxonomy.md`](./verifier-config-error-taxonomy.md)
- [`verifier-loop.md`](./verifier-loop.md)
- [`versioned-column-encryption.md`](./versioned-column-encryption.md)
- [`webhook-retry-queue.md`](./webhook-retry-queue.md)
