<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->


# Relaticle: multi-tenant CRM + AI-assistant foundation

## Use this for
Use when building queued CSV/data import pipelines (match-then-execute with review states), per-unit scratch relational stores, agent assistants that propose writes needing human approval, streamed LLM turns over websockets with billing, custom-field dynamic validation and EAV upserts, or Model Context Protocol (MCP) server endpoints over multi-tenant business data. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval. AGPL-3.0 source: learn patterns and contracts only, never copy code verbatim.

## Load the matching source dump
- `./import-store-throwaway-sqlite.md` — how does one import get its own relational store without polluting the app database?
- `./import-store-bulk-match-update.md` — how do tens of thousands of resolved matches land without a per-row UPDATE?
- `./import-sqlite-row-store.md` — SQLite row storage with ULID traversal guards and payload schema constraints.
- `./import-temp-table-bulk-json-update.md` — bulk JSON-extracted match resolution updates via temporary join tables.
- `./import-header-auto-mapping.md` — header normalization and fuzzy target field resolution.
- `./import-type-inference.md` — statistical column type inference over sampled CSV payloads.
- `./import-choice-resolution.md` — single/multi-choice select option validation and dynamic option minting.
- `./import-timezone-anchoring.md` — date and timestamp parsing with per-tenant timezone anchoring.
- `./match-resolver-set-semantics.md` — how does every imported row get a Create/Update/Skip verdict before execution starts?
- `./import-match-resolution-ladder.md` — multi-pass match resolution ladder with fallback strategies.
- `./entity-link-resolver-normalization.md` — how do CSV strings become record ids across columns, team members, and custom-field JSON values?
- `./import-entity-link-resolver.md` — multi-driver entity link resolution across column, pivot, and custom field boundaries.
- `./import-entity-link-validation.md` — tenant-scoped existence and permission validation for referenced entities.
- `./import-auto-create-relations.md` — in-pipeline auto-creation and deduplication of referenced relation records.
- `./import-intra-run-dedup.md` — intra-run duplicate detection preventing duplicate entity insertion in a single batch.
- `./execute-import-resumable-pipeline.md` — how does a 3-try queued import survive crashes without duplicating records or losing counts?
- `./import-executor-count-last.md` — count-last transaction execution ensuring metrics reflect committed writes only.
- `./withheld-cell-semantics.md` — how does "reviewer skipped this cell" stay different from "the cell was empty"?
- `./import-key-presence-semantics.md` — explicit key-presence vs omitted-key update semantics preventing accidental data wiping.
- `./custom-field-batch-plane.md` — how do thousands of heterogeneous typed values land exactly-once without N queries?
- `./import-customfield-value-upsert.md` — batch upsert pipeline for typed EAV custom field values.
- `./entity-link-storage-strategies.md` — how do three relationship kinds share one import-time resolution contract?
- `./import-entity-link-storage-strategies.md` — relationship persistence strategies for foreign keys, morph-to-many, and custom links.
- `./import-failure-ledger.md` — per-row failure isolation and error reporting without aborting the batch.
- `./customfields-definition-write-integrity.md` — custom field schema definition updates with type immutability rules.
- `./customfields-dynamic-validation.md` — dynamic validation rule compilation based on custom field configuration.
- `./customfields-tag-promotion-activity.md` — promotion of transient tags to first-class metadata with audit logging.
- `./customfields-system-field-enums.md` — system vs user-defined field distinction and reserved namespace protection.
- `./customfields-date-surface-consistency.md` — date surface formatting and timezone-neutral storage consistency.
- `./customfields-model-swap-schema-resources.md` — polymorphic model schema binding and resource projection.
- `./chat-turn-serialization-retries.md` — which failures release-and-retry, which fail immediately, and how is single-writer-per-conversation enforced?
- `./chat-stream-job-retry-taxonomy.md` — transient vs terminal streaming error classification and backoff policies.
- `./pending-action-approval-protocol.md` — what stands between an agent's proposed CRM mutation and the database?
- `./chat-proposal-gated-writes.md` — two-phase proposal and execution gate for AI agent write actions.
- `./chat-resolved-reinjection.md` — re-injecting human approval/rejection outcomes into active prompt context.
- `./stream-event-broadcast-discipline.md` — which agent stream events reach the browser, and in what shape?
- `./failed-turn-coherence-backfill.md` — after a mid-stream crash, what gets written so reload still makes sense?
- `./chat-failed-turn-backfill.md` — synthetic assistant message backfill maintaining conversation transcript continuity.
- `./context-ledger-anchor-reservation.md` — how does bounded recency memory keep the conversation's oldest referenced record from falling off?
- `./chat-context-ledger.md` — bounded context sliding window with high-priority record anchor preservation.
- `./credit-reservation-ledger.md` — what makes every credit mutation idempotent, mutually exclusive per turn, and orphan-recoverable?
- `./chat-credit-reservation-ledger.md` — two-phase credit hold, settlement, and automatic refund on failed turns.
- `./mcp-base-tool-family.md` — base tool abstraction, parameter validation, and response envelope formatting for MCP.
- `./mcp-token-ability-gating.md` — API token scoping and fine-grained ability checking for MCP endpoints.
- `./mcp-customfield-query-plane.md` — querying and filtering custom fields via standardized MCP tool schemas.
- `./mcp-crm-summary-resource.md` — aggregated workspace and pipeline summary resource exposure over MCP.
- `./mcp-relationship-expansion.md` — depth-bounded entity relation expansion in MCP tool outputs.
- `./mcp-canonical-record-urls.md` — one builder/parser pair so search citations and fetch resolution agree, with index-modal deep links for pageless entities.
- `./mcp-annotation-enumeration-audit.md` — reflect the server's own tool registry so every registered tool declares the open-world annotation.
- `./mcp-connector-revocation-ladder.md` — transactional three-table revocation (refresh + auth codes + access) with token-table-derived connector lists.
- `./mcp-oauth-route-registration.md` — boot-deferred route override with the package's canonical route name, plus split pre-auth/authenticated throttle domains.
- `./mcp-create-provenance-stamping.md` — shared-action delegation with an explicit CreationSource enum and unknown-code-rejecting custom-field validation.
- `./mcp-schema-resource-generation.md` — per-entity JSON schema resources assembled from one cached tenant-aware resolver so the model reads live custom-field contracts before writing.
- `./action-interior-contract.md` — one readonly action class per CRUD verb composing policy, tenant-FK validation, custom-field merge, transaction, and eager-load for every calling surface.
- `./v1-resource-eav-serialization.md` — JSON:API resource serialization with orphan-filtered EAV projection and id+label choice rendering shared by REST and MCP.
- `./mcp-tenant-array-relationship-validation.md` — one data-aware rule prefetching a single tenant-scoped id set for a whole array while keeping per-index validation errors.
- `./anthropic-dual-cache-breakpoints.md` — how does a top-level cache_control key add automatic caching of the growing agent-loop transcript on top of the static-prefix breakpoint?
- `./sysadmin-billing-transfer.md` — how does a sysadmin move a Stripe customer and every subscription between two owned workspaces without touching the subscription in Stripe?
- `./refusal-halt-modal.md` — how do you keep a Filament action modal open after a caught business refusal, with infrastructure failures left to error tracking?
- `./member-select-distinct-ordering.md` — how do you pin the acting user to the top of a relationship select without breaking SELECT DISTINCT on Postgres?
- `./onboarding-cap-exemption.md` — how does a wizard run survive having pushed its own user to the workspace-ownership cap?
- `./onboarding-invite-send-loop.md` — what per-address failure taxonomy and circuit breaker keep N invitation sends from stranding a half-finished registration?
- `./invite-join-autoverify.md` — what is the full token-join decision ladder, and how does an invited email skip verification via exact-match?
- `./slug-auto-generation.md` — how does a name→handle field pair regenerate until first user edit, with a CJK-safe fallback?
- `./llms-txt-agent-index.md` — how is an /llms.txt agent index generated so it cannot drift from the pages it lists?
- `./vary-accept-negotiation.md` — why must every content-negotiated variant of a URL declare Vary: Accept, and how is it appended idempotently?
- `./dockerhub-stale-while-error.md` — how does a third-party metric counter survive an upstream outage without overstating or dropping to zero?
- `./agent-sequential-write-enforcement.md` — how does an approval-gated agent get prevented from firing two write tools in one turn?
- `./chat-write-proposal-envelope.md` — what should an LLM write tool return so N mutations land as one reviewable card?
- `./llm-customfield-label-bridge.md` — how do assistants speak option labels yet persist typed EAV option ids safely?
- `./ai-model-resolution-ladder.md` — which model wins when preference, plan, and provider configuration disagree?
- `./conversation-title-pipeline.md` — how are conversations auto-named without clobbering a user rename mid-generation?
- `./orphan-reservation-sweeper.md` — how do dead turns release credit holds without refund+settle ever both applying?
- `./chat-page-context-url-binding.md` — how does an embedded assistant learn which record the user is viewing from a client-supplied URL without trusting it?
- `./follow-up-chip-suggestion.md` — how are deterministic post-turn follow-up suggestions generated from tool calls, and why do write turns get none?
- `./my-tasks-calendar-severity.md` — how are per-user overdue/today boundaries computed over UTC-stored EAV due dates across DST?
- `./proposal-edit-before-approval.md` — how does a human edit a pending agent proposal with full re-validation while the action stays unexecuted?
- `./team-bootstrap-listeners.md` — how does a new tenant get its system-defined custom fields, option colors, and demo data on creation?
- `./credit-seeding-billing-period.md` — how is a per-team credit allowance seeded exactly once, with a billing period that survives month-end anniversary anchors?
- `./scheduled-deletion-ladder.md` — how do scheduled account deletions get exactly-once reminders and a swappable purge?
- `./provider-health-plane.md` — how do you patch an LLM SDK wire-format bug narrowly and health-check providers without spending tokens?
- `./pennant-config-features.md` — what is the minimal feature-flag shape when flags are config-only?
- `./task-digest-timezone-banding.md` — how does one hourly cron send "daily at 08:00 local time" digests without loading the whole user table or double-sending?
- `./deferred-assignee-notification.md` — how do you notify only newly assigned users without making notification failure part of the save request?
- `./kanban-eav-board-move.md` — how does a kanban board work when its columns are custom-field option values in a polymorphic EAV table?
- `./scheduled-deletion-interstitial.md` — how do you lock a scheduled-for-deletion user out while guaranteeing cancel and logout stay reachable?
- `./user-side-deletion-surface.md` — how does a user schedule account deletion, and what blocks it when they still own staffed workspaces?
- `./webhook-listener-fanout.md` — how should webhook and ESP listeners fail, and how do they avoid emitting for rolled-back transactions?
- `./crm-model-concern-stack.md` — how are five CRM entities composed so tenancy, EAV, logging, and ordering stay uniform, and what does the activity log exclude?
- `./notification-preferences-override-matrix.md` — how does a per-cell notification preference UI stay in sync with the gates that consume it while storing only overrides?
- `./tenant-fk-write-guards.md` — how do write actions reject cross-tenant id arrays and partial custom-field patches without trusting the client?
- `./plan-sync-downgrade-ladder.md` — when a Stripe subscription changes, when may the team's plan go down, and why must billing side-effects never block lifecycle operations?
- `./token-bound-team-context.md` — how does an OAuth-chosen team ride on the access token, survive refresh grants, and become the authoritative tenant scope for API calls?
- `./event-suppressed-demo-seeding.md` — how do you seed demo data through models whose observers, sort ordering, and EAV writers you deliberately switched off?
- `./consent-stamped-workspace-access.md` — how does OAuth consent refuse a workspace that cannot use the API, and how does the chosen team reach the auth-code row Passport writes?
- `./plan-gated-chat-rate-limits.md` — how does a per-minute send limit follow the workspace's plan, and what should a 429 tell the client?
- `./queued-export-timezone-columns.md` — how does a CSV produced by a sessionless queued job show datetimes in the requesting user's local time, including columns the framework pre-built?
- `./turn-finalize-ordering.md` — after a streamed agent turn ends, in what order do settlement, persistence, and broadcast run, and what does each failure mode cost?
- `./billing-ui-server-gates.md` — a Livewire billing button may be hidden but its action method stays reachable, so which owner/flag/eligibility gates must be re-run inside each server-side method, and how do checkout failures degrade?
- `./credit-pack-admission-ladder.md` — how do configured price, paid-session, metadata, and customer gates prevent premature prepaid-credit grants?
- `./provider-stream-start-gate.md` — how does a non-blocking per-provider stream-start limiter defer fairly and fail open when Redis is unavailable?
- `./assistant-text-exact-collapse.md` — when can exact whole-string repetition be collapsed consistently across plain-text and TipTap persistence?
- `./chat-side-panel-transcript-lifecycle.md` — how can an embedded panel switch transcripts without losing page context or deleting another user's conversation?

## Capsule map
- **Import scratch storage** — `import-store-throwaway-sqlite`, `import-store-bulk-match-update`, `import-sqlite-row-store`, `import-temp-table-bulk-json-update`: ULID-keyed sqlite file + runtime connection registration, temp-table staging with single join update, payload schema triggers.
- **Import mapping & resolution** — `import-header-auto-mapping`, `import-type-inference`, `import-choice-resolution`, `import-timezone-anchoring`, `match-resolver-set-semantics`, `import-match-resolution-ladder`, `entity-link-resolver-normalization`, `import-entity-link-resolver`, `import-entity-link-validation`, `import-auto-create-relations`, `import-intra-run-dedup`: header fuzzy matching, type inference, set-based match resolution, multi-driver link resolution, intra-run deduplication.
- **Import execution & bulk writes** — `execute-import-resumable-pipeline`, `import-executor-count-last`, `withheld-cell-semantics`, `import-key-presence-semantics`, `custom-field-batch-plane`, `import-customfield-value-upsert`, `entity-link-storage-strategies`, `import-entity-link-storage-strategies`, `import-failure-ledger`: resumable pipeline, count-last transaction execution, key-presence cell semantics, 500-chunk EAV upserts, relationship storage strategies, isolated failure ledger.
- **Custom fields metadata & validation** — `customfields-definition-write-integrity`, `customfields-dynamic-validation`, `customfields-tag-promotion-activity`, `customfields-system-field-enums`, `customfields-date-surface-consistency`, `customfields-model-swap-schema-resources`: schema definition immutability, dynamic validation rules, tag promotion, system field protection, date surface consistency.
- **AI chat orchestration & safety** — `chat-turn-serialization-retries`, `chat-stream-job-retry-taxonomy`, `pending-action-approval-protocol`, `chat-proposal-gated-writes`, `chat-resolved-reinjection`, `stream-event-broadcast-discipline`, `failed-turn-coherence-backfill`, `chat-failed-turn-backfill`, `context-ledger-anchor-reservation`, `chat-context-ledger`: serialized turns, retry taxonomy, human approval gating for CRM mutations, stream event sanitization, coherence backfilling, anchor-reserved bounded memory.
- **Billing & MCP tool surface** — `credit-reservation-ledger`, `chat-credit-reservation-ledger`, `mcp-base-tool-family`, `mcp-token-ability-gating`, `mcp-customfield-query-plane`, `mcp-crm-summary-resource`, `mcp-relationship-expansion`: two-phase credit metering, token-gated MCP tools, custom field MCP querying, CRM summary resources, relationship expansion.
- **Agent-loop economics** — `anthropic-dual-cache-breakpoints`: static-prefix block marker + top-level automatic-cache key so multi-step loops stop re-reading the transcript at full price.
- **Billing transfer (sysadmin)** — `sysadmin-billing-transfer`, `refusal-halt-modal`: customer-handover-not-subscription-rewrite, narrow TransferRefused exception, halt-after-notification modal semantics.
- **Team membership UX** — `member-select-distinct-ordering`, `onboarding-cap-exemption`, `onboarding-invite-send-loop`, `invite-join-autoverify`, `slug-auto-generation`: DISTINCT-safe current-user-first pickers, run-scoped cap exemption, classify-never-throw invite fan-out with a one-refusal circuit breaker, token-join ladder with exact-match auto-verification, flag-arbitrated slug generation.
- **Content negotiation & agent discovery** — `llms-txt-agent-index`, `vary-accept-negotiation`, `dockerhub-stale-while-error`: manifest-generated llms.txt with route-gated sections, symmetric Vary: Accept across variants, dual-key stale-while-error metric counters.
- **Assistant runtime kernel** — `agent-sequential-write-enforcement`, `chat-write-proposal-envelope`, `llm-customfield-label-bridge`, `ai-model-resolution-ladder`, `conversation-title-pipeline`, `orphan-reservation-sweeper`: provider-enforced sequential writes over a three-layer guard ladder, never-persisting write tools with batch proposal envelopes and skip reporting, one shared case-insensitive label→id custom-field bridge, capability×connectivity×entitlement model resolution with silent-degrade chain and hard terminal error, CAS-guarded cheapest-model conversation titling with multibyte-safe sanitization, and key-rewrite orphan reservation sweeps.
- **Assistant context & follow-up plane** — `chat-page-context-url-binding`, `follow-up-chip-suggestion`, `my-tasks-calendar-severity`, `proposal-edit-before-approval`: double-validated client-URL page binding with DB-derived labels and untrusted-data prompt fencing, zero-cost deterministic follow-up chips suppressed on write turns, local-midnight day boundaries over UTC EAV due dates with one-round-trip field metadata, and locked re-validating pre-approval proposal editing with per-code merge semantics.
- **Tenant bootstrap & lifecycle** — `team-bootstrap-listeners`, `credit-seeding-billing-period`, `scheduled-deletion-ladder`, `provider-health-plane`, `pennant-config-features`: enum-driven per-tenant custom-field bootstrap with a post-create color pass, lock-guarded exactly-once credit seeding over an anchor-recomputed anniversary-cycle resolver, day-window reminder + contract-delegated purge deletion ladder, a narrowly-patched Anthropic gateway with a retrieve-don't-generate provider health check, and config-resolving Pennant flag classes.
- **Digest & notification plane** — `task-digest-timezone-banding`, `deferred-assignee-notification`: indexed timezone-band recipient filtering with a per-user triple gate over a local-midnight EAV window, and diff-gated response-deferred assignee fan-out with per-channel preference gates.
- **Board & domain-model plane** — `kanban-eav-board-move`, `crm-model-concern-stack`: left-joined EAV column values with transactional position+column moves and date-string vs zone-converted badge disciplines, over a uniform five-entity concern stack with fail-closed tenancy and EAV-excluding activity logs.
- **Account deletion & listener fan-out** — `scheduled-deletion-interstitial`, `user-side-deletion-surface`, `webhook-listener-fanout`: a both-directions-agreeing interstitial gate with an always-open exit, ownership-refused user deletion stamping user + personal team together, and webhook/ESP listeners with silent early-returns, release-not-drop retries, and afterCommit dispatch.
- **Preferences, write-guards & API context** — `notification-preferences-override-matrix`, `tenant-fk-write-guards`, `plan-sync-downgrade-ladder`, `token-bound-team-context`, `event-suppressed-demo-seeding`: overrides-only preference storage behind one shared predicate, count-equality tenant-FK guards with merge-before-save EAV patches, provenance-gated plan downgrades with log-never-throw billing cancellation, consent-time team binding carried on tokens through refresh grants with memory-only request scoping, and event-suppressed fixture seeding with hand-reimplemented sort ordering.
- **Consent, limits & export plane** — `consent-stamped-workspace-access`, `plan-gated-chat-rate-limits`, `queued-export-timezone-columns`, `turn-finalize-ordering`: consent-time billing-health refusal with a session-put/creating-hook-pull stamp into a framework-owned persistence point, plan-enum limits over team-keyed buckets with a structured Retry-After-echoing 429, two-site timezone resolution for sessionless queued exports with header-named zones and entity-scoped custom-field re-wrapping, and a fixed meter-then-persist finalize ladder with per-mode failure costs.
- **MCP surface completion** — `mcp-canonical-record-urls`, `mcp-annotation-enumeration-audit`, `mcp-connector-revocation-ladder`, `mcp-oauth-route-registration`, `mcp-create-provenance-stamping`: one builder/parser URL pair with index-modal deep links for pageless entities, registry-reflection annotation enumeration so a new tool cannot skip the policy, transactional three-table connector revocation with a token-table-derived connector list, boot-deferred OAuth route override with split throttle domains, and shared-action create delegation with an explicit provenance enum and unknown-code-rejecting custom-field validation.
- **Schema, actions & serialization plane** — `mcp-schema-resource-generation`, `action-interior-contract`, `v1-resource-eav-serialization`, `mcp-tenant-array-relationship-validation`: cached tenant-aware schema resources feeding the model's write contracts, readonly per-verb action classes as the single policy/tenant/transaction funnel, orphan-filtered EAV resource serialization shared by REST and MCP, and batched data-aware array relationship validation with per-index errors.
- **Billing UI server-side gating** — `billing-ui-server-gates`: per-method re-gating of a Livewire billing page whose buttons render conditionally but whose action methods stay reachable, with checkout-failure degradation carried through URL return state.
- **Billing and chat stream-support plane** — `credit-pack-admission-ladder`, `provider-stream-start-gate`, `assistant-text-exact-collapse`, `chat-side-panel-transcript-lifecycle`: paid payment-mode/customer-bound credit-pack admission before idempotent ledger fulfillment, non-blocking provider-partitioned starts with jittered release and Redis fail-open, exact whole-string assistant echo collapse at independent persistence sites, and orthogonal side-panel context/transcript state with ownership-safe deletion.

## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
relaticle (AGPL-3.0), `main@6e3bf8dfb7c5dcc97765fcba6fdf62585c541e1b` (= base_sha after pass-2 drift re-index, 13 upstream commits past the pass-1 pin `2c2a2456`); Codebase Memory project `relaticle` — root `$REFERENCE_ROOT/relaticle` (canonical worktree `$REFERENCE_ROOT/platforms/relaticle`, fast-forwarded to origin/main this pass), branch main, full mode, 19,857 nodes / 95,556 edges, parse_partial = 20 files (blade views + compiled CSS only, none cited), skipped = 0, not_indexed = 8 dirs + 84 image/suffix files by design (recounted at pass-3 status check).

## Full view (memory graph)
Revalidate `relaticle` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Pass 1: `index_status --project relaticle --verbose` confirmed HEAD `2c2a2456…` = base_sha, mode full. stdin-JSON `check_index_coverage` over all cited source paths returned `no_recorded_issue` + `metadata_match`. Direct Pest suites exist and are cited per capsule (`tests/Feature/ImportWizard/**`, `tests/Feature/Chat/**`, `tests/Feature/Mcp/**`). Pass 2 (2026-08-24): re-indexed in place at new HEAD `6e3bf8df…` = base_sha after fast-forward; 13-commit drift mined diff-first into 9 new capsule-v2 (chat caching, billing transfer, onboarding, negotiation planes); no stale twin. AGPL: mine behavior contracts; never lift code verbatim. Pass 3 (2026-08-26): pin unchanged (`6e3bf8df…` == HEAD == base_sha, live-verified; generation 2026-08-24T14:02:51Z, full mode 19,857n/95,556e); ledger row reconciled from stale pass-0; work record created at `inspo/relaticle-work/`; deepen/re-mine batch added the assistant-runtime-kernel group (+6 capsule-v2: sequential-write enforcement, write-proposal envelope, custom-field label bridge, model resolution ladder, title pipeline, orphan reservation sweeper) with all 20 newly-cited source/test paths `no_recorded_issue` + `metadata_match`; Pest runner blocked (no vendor/php on PATH) so Gate 5 used deterministic probe + retrieval evidence. Pass 4 (2026-08-27): pin unchanged (`6e3bf8df…` == HEAD, live-verified, clean tree); Codebase Memory MCP not connected this session → direct source+test reading fallback per AGENTS.md; +4 capsule-v2 assistant context & follow-up plane (chat-page-context-url-binding, follow-up-chip-suggestion, my-tasks-calendar-severity, proposal-edit-before-approval) over `packages/Chat/src/Services/{ChatContextService,FollowUpService,MyTasksService,ProposalEditor}.php` + send-path re-validation + display re-render support, all cited paths read directly at HEAD. Pass 5 (2026-08-27): pin unchanged (`6e3bf8df…` == HEAD, live-verified, clean tree); MCP still not connected → direct-read fallback; +5 capsule-v2 tenant bootstrap & lifecycle group (team-bootstrap-listeners, credit-seeding-billing-period, scheduled-deletion-ladder, provider-health-plane, pennant-config-features) over `app/Listeners/*`, `app/Features/*`, `app/Actions/Chat/SeedTeamCreditBalance.php`, `packages/Chat/src/Services/CreditPeriodResolver.php`, `app/Console/Commands/PurgeScheduledDeletionsCommand.php`, `app/Actions/Jetstream/*Deletion*.php`, `app/Ai/*`, `app/Health/ChatProviderCheck.php`, all read directly at HEAD with their Pest tests. Pass 6 (2026-08-27): pin unchanged (`6e3bf8df…` == HEAD, live-verified, clean tree); MCP still not connected → direct-read fallback; +7 capsule-v2 (task-digest-timezone-banding, deferred-assignee-notification, kanban-eav-board-move, scheduled-deletion-interstitial, user-side-deletion-surface, webhook-listener-fanout, crm-model-concern-stack) over `app/Console/Commands/SendTaskDigestCommand.php`, `app/Services/Notifications/DigestService.php`, `app/Actions/Task/NotifyTaskAssignees.php`, `app/Filament/Resources/{TaskResource,OpportunityResource}/Pages/*Board.php`, `app/Actions/Jetstream/{Schedule,Cancel}UserDeletion.php`, `app/Http/Middleware/CheckScheduledDeletion.php`, `app/Livewire/App/Profile/ScheduledDeletionInterstitial.php`, `app/Listeners/{Billing,Email}/*`, `app/Models/{Opportunity,Task,Export}.php` + Concerns/Scopes, all read directly at HEAD with their Pest tests; description trimmed to 1002 chars to keep validator P0 clear. Pass 8 (2026-08-27): pin unchanged (`6e3bf8df…` == HEAD, live-verified, clean tree); MCP still not connected → direct-read fallback; +4 capsule-v2 consent/limits/export/finalize group (consent-stamped-workspace-access, plan-gated-chat-rate-limits, queued-export-timezone-columns, turn-finalize-ordering) over `app/Http/Controllers/Mcp/ApproveAuthorizationController.php`, `app/Models/Passport/AuthCode.php`, `app/Services/Billing/HostedWorkspaceAccess.php`, `app/Enums/Plan.php` + `app/Providers/AppServiceProvider.php` rate limiters, `app/Filament/Exports/BaseExporter.php` + exemplar exporters, `packages/Chat/src/Jobs/ProcessChatMessage.php` interior, all read directly at HEAD with their Pest tests; description left at 1002 chars (new vocabulary carried by loader/map lines). Pass 9 (2026-08-27): pin unchanged (`6e3bf8df…` == HEAD, live-verified, clean tree); MCP still not connected → direct-read fallback; +5 capsule-v2 MCP-surface-completion group (mcp-canonical-record-urls, mcp-annotation-enumeration-audit, mcp-connector-revocation-ladder, mcp-oauth-route-registration, mcp-create-provenance-stamping) over `app/Support/CanonicalRecordUrl.php`, `app/Mcp/Tools/{SearchTool,FetchTool,BaseCreateTool,BaseUpdateTool,BaseDeleteTool,BaseAttachTool,BaseDetachTool,BaseShowTool,BaseListTool}.php`, `app/Mcp/Tools/Task/ListTasksTool.php`, `app/Mcp/Tools/Note/ListNotesTool.php`, `app/Mcp/Servers/RelaticleServer.php`, `app/Rules/ValidCustomFields.php`, `app/Enums/CreationSource.php`, `app/Actions/Mcp/RevokeOAuthConnector.php`, `app/Livewire/App/AccessTokens/ManageOAuthConnectors.php`, `routes/ai.php`, all read directly at HEAD with their Pest tests; description left at 1002 chars (new vocabulary carried by loader/map lines). Pass 10 (2026-08-28): pin unchanged (`6e3bf8df…` == HEAD, live-verified, clean tree); MCP still not connected → direct-read fallback; +4 capsule-v2 schema/actions/serialization group (mcp-schema-resource-generation, action-interior-contract, v1-resource-eav-serialization, mcp-tenant-array-relationship-validation) over `app/Mcp/Resources/TaskSchemaResource.php` + `Concerns/ResolvesEntitySchema.php`, `app/Mcp/Prompts/CrmOverviewPrompt.php`, `app/Actions/{Company,Opportunity}/{Create,Update,List,Delete}*.php`, `app/Http/Resources/V1/TaskResource.php` + `Concerns/FormatsCustomFields.php`, `app/Mcp/Tools/BaseUpdateTool.php`, `app/Mcp/Tools/Task/{UpdateTaskTool,AttachTaskToEntitiesTool,DetachTaskFromEntitiesTool}.php`, `app/Rules/ArrayExistsForTeam.php`, `app/Mcp/Schema/CustomFieldFilterSchema.php` + `app/Providers/AppServiceProvider.php` invalidation hook, all read directly at HEAD with their Pest tests (SchemaResourcesTest, TasksApiTest, ArrayExistsForTeamTest); description left at 1002 chars (new vocabulary carried by loader/map lines).

## Boundaries
Adopt the pure contracts: throwaway per-unit stores, resolve-then-bulk-apply, total-disposition stamps, checkpointed resumable writers, tri-state cell semantics, strategy-split relationship writing, retry taxonomy with independent ceilings, allowlisted human-approval state machines, journal-first metering with orphan sweepers, anchor-reserved bounded memory, dual-breakpoint prompt caching, customer-handover billing transfer with narrow refusals, run-scoped cap exemptions, classify-never-throw fan-outs, manifest-generated agent indexes. Adapt host mechanics: Laravel queue/broadcast/container idioms to your framework, Reverb to your websocket layer, Filament/Livewire surfaces to your UI, the custom-fields vendor schema to your EAV shape. Omit product surface: marketing routes/pages (mega menu, compare pages, works-with strip beyond the DockerHub pattern), Stripe checkout flows, Scribe API docs, SystemAdmin panels beyond the transfer action, Chat package UI components. Never copy code verbatim (AGPL-3.0) — these capsules document behavior to reimplement independently.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`action-interior-contract.md`](./action-interior-contract.md)
- [`agent-sequential-write-enforcement.md`](./agent-sequential-write-enforcement.md)
- [`ai-model-resolution-ladder.md`](./ai-model-resolution-ladder.md)
- [`anthropic-dual-cache-breakpoints.md`](./anthropic-dual-cache-breakpoints.md)
- [`assistant-text-exact-collapse.md`](./assistant-text-exact-collapse.md)
- [`billing-ui-server-gates.md`](./billing-ui-server-gates.md)
- [`chat-context-ledger.md`](./chat-context-ledger.md)
- [`chat-credit-reservation-ledger.md`](./chat-credit-reservation-ledger.md)
- [`chat-failed-turn-backfill.md`](./chat-failed-turn-backfill.md)
- [`chat-page-context-url-binding.md`](./chat-page-context-url-binding.md)
- [`chat-proposal-gated-writes.md`](./chat-proposal-gated-writes.md)
- [`chat-resolved-reinjection.md`](./chat-resolved-reinjection.md)
- [`chat-side-panel-transcript-lifecycle.md`](./chat-side-panel-transcript-lifecycle.md)
- [`chat-stream-job-retry-taxonomy.md`](./chat-stream-job-retry-taxonomy.md)
- [`chat-turn-serialization-retries.md`](./chat-turn-serialization-retries.md)
- [`chat-write-proposal-envelope.md`](./chat-write-proposal-envelope.md)
- [`consent-stamped-workspace-access.md`](./consent-stamped-workspace-access.md)
- [`context-ledger-anchor-reservation.md`](./context-ledger-anchor-reservation.md)
- [`conversation-title-pipeline.md`](./conversation-title-pipeline.md)
- [`credit-pack-admission-ladder.md`](./credit-pack-admission-ladder.md)
- [`credit-reservation-ledger.md`](./credit-reservation-ledger.md)
- [`credit-seeding-billing-period.md`](./credit-seeding-billing-period.md)
- [`crm-model-concern-stack.md`](./crm-model-concern-stack.md)
- [`custom-field-batch-plane.md`](./custom-field-batch-plane.md)
- [`customfields-date-surface-consistency.md`](./customfields-date-surface-consistency.md)
- [`customfields-definition-write-integrity.md`](./customfields-definition-write-integrity.md)
- [`customfields-dynamic-validation.md`](./customfields-dynamic-validation.md)
- [`customfields-model-swap-schema-resources.md`](./customfields-model-swap-schema-resources.md)
- [`customfields-system-field-enums.md`](./customfields-system-field-enums.md)
- [`customfields-tag-promotion-activity.md`](./customfields-tag-promotion-activity.md)
- [`deferred-assignee-notification.md`](./deferred-assignee-notification.md)
- [`dockerhub-stale-while-error.md`](./dockerhub-stale-while-error.md)
- [`entity-link-resolver-normalization.md`](./entity-link-resolver-normalization.md)
- [`entity-link-storage-strategies.md`](./entity-link-storage-strategies.md)
- [`event-suppressed-demo-seeding.md`](./event-suppressed-demo-seeding.md)
- [`execute-import-resumable-pipeline.md`](./execute-import-resumable-pipeline.md)
- [`failed-turn-coherence-backfill.md`](./failed-turn-coherence-backfill.md)
- [`follow-up-chip-suggestion.md`](./follow-up-chip-suggestion.md)
- [`import-auto-create-relations.md`](./import-auto-create-relations.md)
- [`import-choice-resolution.md`](./import-choice-resolution.md)
- [`import-customfield-value-upsert.md`](./import-customfield-value-upsert.md)
- [`import-entity-link-resolver.md`](./import-entity-link-resolver.md)
- [`import-entity-link-storage-strategies.md`](./import-entity-link-storage-strategies.md)
- [`import-entity-link-validation.md`](./import-entity-link-validation.md)
- [`import-executor-count-last.md`](./import-executor-count-last.md)
- [`import-failure-ledger.md`](./import-failure-ledger.md)
- [`import-header-auto-mapping.md`](./import-header-auto-mapping.md)
- [`import-intra-run-dedup.md`](./import-intra-run-dedup.md)
- [`import-key-presence-semantics.md`](./import-key-presence-semantics.md)
- [`import-match-resolution-ladder.md`](./import-match-resolution-ladder.md)
- [`import-sqlite-row-store.md`](./import-sqlite-row-store.md)
- [`import-store-bulk-match-update.md`](./import-store-bulk-match-update.md)
- [`import-store-throwaway-sqlite.md`](./import-store-throwaway-sqlite.md)
- [`import-temp-table-bulk-json-update.md`](./import-temp-table-bulk-json-update.md)
- [`import-timezone-anchoring.md`](./import-timezone-anchoring.md)
- [`import-type-inference.md`](./import-type-inference.md)
- [`invite-join-autoverify.md`](./invite-join-autoverify.md)
- [`kanban-eav-board-move.md`](./kanban-eav-board-move.md)
- [`llm-customfield-label-bridge.md`](./llm-customfield-label-bridge.md)
- [`llms-txt-agent-index.md`](./llms-txt-agent-index.md)
- [`match-resolver-set-semantics.md`](./match-resolver-set-semantics.md)
- [`mcp-annotation-enumeration-audit.md`](./mcp-annotation-enumeration-audit.md)
- [`mcp-base-tool-family.md`](./mcp-base-tool-family.md)
- [`mcp-canonical-record-urls.md`](./mcp-canonical-record-urls.md)
- [`mcp-connector-revocation-ladder.md`](./mcp-connector-revocation-ladder.md)
- [`mcp-create-provenance-stamping.md`](./mcp-create-provenance-stamping.md)
- [`mcp-crm-summary-resource.md`](./mcp-crm-summary-resource.md)
- [`mcp-customfield-query-plane.md`](./mcp-customfield-query-plane.md)
- [`mcp-oauth-route-registration.md`](./mcp-oauth-route-registration.md)
- [`mcp-relationship-expansion.md`](./mcp-relationship-expansion.md)
- [`mcp-schema-resource-generation.md`](./mcp-schema-resource-generation.md)
- [`mcp-tenant-array-relationship-validation.md`](./mcp-tenant-array-relationship-validation.md)
- [`mcp-token-ability-gating.md`](./mcp-token-ability-gating.md)
- [`member-select-distinct-ordering.md`](./member-select-distinct-ordering.md)
- [`my-tasks-calendar-severity.md`](./my-tasks-calendar-severity.md)
- [`notification-preferences-override-matrix.md`](./notification-preferences-override-matrix.md)
- [`onboarding-cap-exemption.md`](./onboarding-cap-exemption.md)
- [`onboarding-invite-send-loop.md`](./onboarding-invite-send-loop.md)
- [`orphan-reservation-sweeper.md`](./orphan-reservation-sweeper.md)
- [`pending-action-approval-protocol.md`](./pending-action-approval-protocol.md)
- [`pennant-config-features.md`](./pennant-config-features.md)
- [`plan-gated-chat-rate-limits.md`](./plan-gated-chat-rate-limits.md)
- [`plan-sync-downgrade-ladder.md`](./plan-sync-downgrade-ladder.md)
- [`proposal-edit-before-approval.md`](./proposal-edit-before-approval.md)
- [`provider-health-plane.md`](./provider-health-plane.md)
- [`provider-stream-start-gate.md`](./provider-stream-start-gate.md)
- [`queued-export-timezone-columns.md`](./queued-export-timezone-columns.md)
- [`refusal-halt-modal.md`](./refusal-halt-modal.md)
- [`scheduled-deletion-interstitial.md`](./scheduled-deletion-interstitial.md)
- [`scheduled-deletion-ladder.md`](./scheduled-deletion-ladder.md)
- [`slug-auto-generation.md`](./slug-auto-generation.md)
- [`stream-event-broadcast-discipline.md`](./stream-event-broadcast-discipline.md)
- [`sysadmin-billing-transfer.md`](./sysadmin-billing-transfer.md)
- [`task-digest-timezone-banding.md`](./task-digest-timezone-banding.md)
- [`team-bootstrap-listeners.md`](./team-bootstrap-listeners.md)
- [`tenant-fk-write-guards.md`](./tenant-fk-write-guards.md)
- [`token-bound-team-context.md`](./token-bound-team-context.md)
- [`turn-finalize-ordering.md`](./turn-finalize-ordering.md)
- [`user-side-deletion-surface.md`](./user-side-deletion-surface.md)
- [`v1-resource-eav-serialization.md`](./v1-resource-eav-serialization.md)
- [`vary-accept-negotiation.md`](./vary-accept-negotiation.md)
- [`webhook-listener-fanout.md`](./webhook-listener-fanout.md)
- [`withheld-cell-semantics.md`](./withheld-cell-semantics.md)
