<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->

# Chatwoot: Multi-Tenant Event Fanout, Webhook Dispatch, and Auto-Assignment Foundation

## Use this for
Use when porting Chatwoot-style multi-tenant SaaS mechanics: account-scoped event fanout to per-account webhook subscriptions, HMAC-signed outbound webhook delivery with retry classification, Redis round-robin agent assignment with row-lock race discipline, API-token tenant resolution with bot endpoint allowlists, bit-packed feature flags, and editor-markdown webhook payload hygiene. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./event-dispatch-fanout.md` — How does a model callback fan one event out to every subscribed account webhook plus the channel inbox webhook?
- `./webhook-subscription-model.md` — What makes a webhook subscription row valid, and which events may it receive?
- `./webhook-hmac-delivery.md` — How is an outgoing delivery signed, timed out, and classified for failure handling?
- `./agent-bot-retry-ladder.md` — When does an agent-bot delivery retry instead of failing, and what happens after the last attempt?
- `./webhook-error-compensation.md` — What compensating state change repairs a conversation/message when a delivery fails mid-flight?
- `./safe-fetch-boundary.md` — How do outbound fetches stay SSRF-safe while still allowing private-network deployments?
- `./round-robin-redis-queue.md` — How does a Redis list implement fair round-robin over inbox agents with self-healing membership?
- `./legacy-v1-in-save-assignment.md` — Why must legacy V1 auto-assignment run inside before_save on a locked row?
- `./v2-bulk-assignment-plane.md` — How does bulk V2 assignment coalesce triggers, skip stale backlog, and atomically claim rows?
- `./fair-distribution-rate-limit.md` — How is per-agent assignment volume capped within a sliding window?
- `./api-token-tenant-resolution.md` — How does one access token resolve user vs bot identity across accounts?
- `./bot-endpoint-allowlist.md` — Which endpoints may a bot token call, and where is that enforced?
- `./bitpacked-feature-flags.md` — How are up to 126 features packed into two bigint flag columns from one YAML source of truth?
- `./policy-role-ladder.md` — Which account actions need administrator versus agent membership, and where are policies mounted?
- `./editor-markdown-webhook-normalizer.md` — Why do stored message bodies carry backslash line breaks, and when are they stripped?

## Capsule map
- **Event dispatch fanout** — `event-dispatch-fanout`: listener merges `webhook_data` payloads then fans to account webhooks (subscription-filtered) and API-channel inbox webhooks; account-level gate short-circuits both.
- **Webhook subscription model** — `webhook-subscription-model`: jsonb subscriptions validated as non-empty subset of ALLOWED_WEBHOOK_EVENTS; unique `(account_id,url)`; secret via has_secure_token + encrypts.
- **HMAC webhook delivery** — `webhook-hmac-delivery`: sign `"{timestamp}.{body}"` into `X-Chatwoot-Signature: sha256=...`; GlobalConfig timeout defaulting to 5s; SafeFetch error taxonomy.
- **Agent-bot retry ladder** — `agent-bot-retry-ladder`: RetryableError raised only for agent-bot type on HTTP 429/500; `retry_on ... attempts: 3` then handle_failure closure.
- **Webhook error compensation** — `webhook-error-compensation`: failed bot webhook reopens pending conversations (unless keep_pending_on_bot_failure); failed api-inbox webhook marks the message failed.
- **SafeFetch SSRF boundary** — `safe-fetch-boundary`: ssrf_filter by default, private-network escape hatch streams through a size-capped tempfile with content-type gate.
- **Round-robin Redis queue** — `round-robin-redis-queue`: lpush/lpop-with-requeue list keyed per inbox; queue-vs-members set check self-heals drift; intersection with allowed ids picks the next agent.
- **Legacy V1 in-save assignment** — `legacy-v1-in-save-assignment`: lock the row, drop already-committed status changes, re-check reassignment against merged pending values, mutate in memory so one save carries status+assignee.
- **V2 bulk assignment plane** — `v2-bulk-assignment-plane`: token-gated single-flight job per inbox; age-excluded priority ordering; `FOR UPDATE SKIP LOCKED` claim; manual ASSIGNEE_CHANGED dispatch.
- **Fair distribution rate limit** — `fair-distribution-rate-limit`: one Redis key per (inbox, agent, conversation) with TTL window; count via keys-pattern; policy-configurable limit/window.
- **API token tenant resolution** — `api-token-tenant-resolution`: header presence selects token auth; AccessToken.owner becomes Current.user only for User/AgentBot; suspended accounts rejected; membership sets Current.account_user.
- **Bot endpoint allowlist** — `bot-endpoint-allowlist`: BOT_ACCESSIBLE_ENDPOINTS maps controller paths to action names; bots get conversation/message mutation surface only.
- **Bitpacked feature flags** — `bitpacked-feature-flags`: FlagShihTzu bit columns built at boot from config/features.yml; 63 features max per bigint column; unknown column names raise at boot.
- **Policy role ladder** — `policy-role-ladder`: ApplicationPolicy deny-by-default with pundit user_context {user, account, account_user}; read actions open to agents, mutations/admin surfaces administrator-only.
- **Editor markdown normalizer** — `editor-markdown-webhook-normalizer`: strip CommonMark hard-break backslashes and trailing newlines only in webhook/API projection, never in stored content.

## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
Chatwoot (MIT for app/lib/spec; enterprise/ tree under a separate commercial license), `develop@6154aebcfea1fe62e8dd01fbf94568ef827fc51c`; Codebase Memory project `ext-chatwoot` (ready FULL mode, 285,456 nodes / 364,200 edges, generation 2026-08-23, head == base_sha zero drift; parse_partial ×19 confined to scss/yml/liquid assets, none cited).

## Full view (memory graph)
Revalidate `ext-chatwoot` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. BM25 retrieval plane verified live during pass 1: symbol queries like "Webhooks::Trigger execute retryable", "InboxRoundRobinService available_agent queue", "AccessTokenAuthHelper validate_bot_access_token", and "SafeFetch fetcher stream tempfile max bytes" each resolve rank-1 line-exact.

## Boundaries
Adopt the pure contracts: subscription-filtered dual-target fanout, timestamp-prefixed HMAC signing, retryable-status classification, lock-and-reconcile assignment, token-gated single-flight jobs, bit-packed flags from YAML. Adapt host-specific integration: Rails callbacks/dispatcher, Sidekiq queues, Redis::Alfred helpers, Pundit mounting, GlobalConfig. Omit source-specific behavior: channel/provider adapters (WhatsApp/Twilio/Facebook ingestion), Captain/LLM enterprise plane, cloud billing, SLA engine internals, dashboard Vue UI.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`agent-bot-retry-ladder.md`](./agent-bot-retry-ladder.md)
- [`api-token-tenant-resolution.md`](./api-token-tenant-resolution.md)
- [`bitpacked-feature-flags.md`](./bitpacked-feature-flags.md)
- [`bot-endpoint-allowlist.md`](./bot-endpoint-allowlist.md)
- [`editor-markdown-webhook-normalizer.md`](./editor-markdown-webhook-normalizer.md)
- [`event-dispatch-fanout.md`](./event-dispatch-fanout.md)
- [`fair-distribution-rate-limit.md`](./fair-distribution-rate-limit.md)
- [`legacy-v1-in-save-assignment.md`](./legacy-v1-in-save-assignment.md)
- [`policy-role-ladder.md`](./policy-role-ladder.md)
- [`round-robin-redis-queue.md`](./round-robin-redis-queue.md)
- [`safe-fetch-boundary.md`](./safe-fetch-boundary.md)
- [`v2-bulk-assignment-plane.md`](./v2-bulk-assignment-plane.md)
- [`webhook-error-compensation.md`](./webhook-error-compensation.md)
- [`webhook-hmac-delivery.md`](./webhook-hmac-delivery.md)
- [`webhook-subscription-model.md`](./webhook-subscription-model.md)
