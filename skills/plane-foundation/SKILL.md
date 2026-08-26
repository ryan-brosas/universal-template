---
name: plane-foundation
description: "Use when porting multi-instance CRDT document collaboration (a Hocuspocus/Yjs live server bolted onto an HTTP API backend) or SSRF-safe outbound HTTP with signed webhook delivery (fail-closed IP classification, DNS-rebinding-proof pinned fetches, manual redirect ladders, celery delivery/retry/deactivation). Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."
---
# Plane foundation: realtime collaboration + SSRF-safe outbound/webhook planes

## Use this for
Use when porting multi-instance CRDT document collaboration (a Hocuspocus/Yjs live server bolted onto an HTTP API backend) or SSRF-safe outbound HTTP with signed webhook delivery (fail-closed IP classification, DNS-rebinding-proof pinned fetches, manual redirect ladders, celery delivery/retry/deactivation). Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/live-hocuspocus-bootstrap-lifecycle.md` — what order must redis, hocuspocus, routes, and shutdown run in, and why is extension order load-bearing?
- `references/live-page-binary-empty-fallback.md` — how do you serve a CRDT document when storage still only has legacy HTML?
- `references/live-store-413-force-close-unload.md` — what does the server do when a collaborative save exceeds the backend size limit?
- `references/live-force-close-choreography.md` — how do you evict every client of one document across a server fleet and guarantee the doc leaves memory?
- `references/live-redis-admin-command-bus.md` — how do instances coordinate admin commands and broadcast stateless events to ALL servers holding a document?
- `references/live-debounced-title-persistence.md` — how do you debounce per-document field writes without losing the last edit or leaking observers?
- `references/live-apperror-sanitization-taxonomy.md` — how do upstream axios errors become safe, branchable errors at the collaboration edge?
- `references/live-ws-auth-cookie-ladder.md` — how do you authenticate a browser WebSocket when cookies may or may not ride the upgrade request?
- `references/api-ip-blocklist-fail-closed.md` — which IP ranges may a server-side fetch never target, and how does the verdict survive IPv6 transition encodings and stdlib drift?
- `references/api-resolve-validate-escape-hatches.md` — how can trusted internal hosts bypass an SSRF block WITHOUT skipping resolution or pinning?
- `references/api-ssrf-pinned-ip-adapter.md` — how do you fetch a user-supplied URL so the validated IP is exactly the reached IP?
- `references/api-manual-redirect-revalidation.md` — how do you follow redirects without letting a 3xx bounce you into the internal network?
- `references/api-webhook-event-fanout.md` — where do diff, subscription filtering, and per-subscriber delivery live, and how do deletions stay safe?
- `references/api-webhook-delivery-envelope.md` — what goes on the webhook wire and how is it signed so receivers verify byte-exactly?
- `references/api-webhook-retry-deactivation-ladder.md` — which failures retry, which deactivate the webhook, and which are only recorded?
- `references/api-webhook-url-admission.md` — what must be true of a webhook URL at create/update time, including the PATCH-context bug class?

## Capsule map
**Realtime collaboration plane (`apps/live`, pass 1)**
- **Bootstrap & shutdown** — `live-hocuspocus-bootstrap-lifecycle`: redis → hocuspocus → routes init ladder, reverse-ish destroy ladder, singleton server manager named `HOSTNAME||uuid`, extension array order is contract.
- **Empty-binary fetch fallback** — `live-page-binary-empty-fallback`: empty stored Yjs binary ⇒ refetch page HTML ⇒ convert ⇒ best-effort write-back ⇒ serve converted bytes.
- **Store triage / 413** — `live-store-413-force-close-unload`: on save failure, statusCode 413 selects typed client error + fleet-wide force close + swallow-don't-throw (hocuspocus finally-block null-doc trap); everything else rethrows after broadcast.
- **Force-close choreography** — `live-force-close-choreography`: notify-local → 50 ms grace → close with custom CloseCode family (4000–4003) → cross-server admin publish → 800 ms wait → unloadDocument → verify-gone.
- **Redis admin bus** — `live-redis-admin-command-bus`: HocuspocusRedis subclass owns pub/sub duplicates, validated handler Map on `hocuspocus:admin`, zero-identifier-byte `broadcastToDocument` so every server processes the stateless payload.
- **Debounced title persistence** — `live-debounced-title-persistence`: XmlFragment observeDeep → per-doc 5 s debounce with AbortController kill of superseded saves, silent AbortError, retry timer on real errors, flush-on-unload, observer side-Map anti-leak.
- **Error taxonomy** — `live-apperror-sanitization-taxonomy`: constructor ladder (self passthrough, string, axios-minimal, AbortError→ABORT_ERROR, Error→name-as-code) that downstream code branches on.
- **WS auth ladder** — `live-ws-auth-cookie-ladder`: token may be JSON `{id, cookie}` else header cookie; typed missing-credential error; server re-validates user id against the cookie before trusting context.

**SSRF-safe outbound HTTP + webhook delivery plane (`apps/api`, pass 2)**
- **IP classification** — `api-ip-blocklist-fail-closed`: stdlib properties + explicit CIDR denylist for version-unstable ranges + recursive decode of IPv4 embedded in IPv6 transitions; fail closed.
- **Escape hatches** — `api-resolve-validate-escape-hatches`: `allowed_ips` networks and exact-match `allowed_hosts`; trusted hosts skip only the block check — resolution still runs and the connection still pins; mixed public+private DNS fails closed.
- **Pinned transport** — `api-ssrf-pinned-ip-adapter`: connect to the validated IP literal via a throwaway session + `server_hostname` injection; Host/SNI/cert keep the real name; trust_env off, null proxies.
- **Redirect policy** — `api-manual-redirect-revalidation`: two exported policies — `pinned_fetch` never follows (event delivery), `pinned_fetch_following_redirects` re-resolves/re-validates/re-pins every hop with a bounded budget.
- **Event fan-out** — `api-webhook-event-fanout`: view → model_activity (per-field diff vs pre-write snapshot, post-commit only) → webhook_activity (flag-column filter, deleted-row stub, race swallow) → one delivery task per active webhook.
- **Delivery envelope** — `api-webhook-delivery-envelope`: DjangoJSONEncoder normalize BEFORE signing; HMAC-SHA256 hex over the exact serialized payload under X-Plane-Signature; id-only task args reloaded in-worker.
- **Retry/deactivate ladder** — `api-webhook-retry-deactivation-ladder`: RequestException retries (600 s backoff × jitter, ≤5) then deactivate + owner email; ValueError (SSRF reject) records 400 without retry or deactivation; every attempt logs one WebhookLog row with retry_count.
- **Admission gate** — `api-webhook-url-admission`: create AND update validate SSRF + disallowed-domains ∪ own-host suffix guard; trusted hosts bypass the domain check; update works only when the view passes `context={"request": request}`.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
Plane (AGPL-3.0-only — reuse these capsules as pattern citations; copying source verbatim carries AGPL obligations), `preview@e056bbf9eb6b511cdc0a5823b1bd6922e561a485`; Codebase Memory project `plane` (ready FULL 83,990n/194,703e @ gen 2026-08-25T19:59:48Z; cited paths no_recorded_issue+metadata_match both passes; parse_partial limited to CSS/env/nginx/email-template files, none cited). Pass 1 (apps/live): no dedicated upstream tests exist for any of its capsules — apps/live ships exactly two vitest suites covering only pdf-export; probes are deterministic source pins. Pass 2 (apps/api SSRF/webhook): direct unit suites exist (`tests/unit/bg_tasks/test_url_security.py`, `test_ssrf_advisories.py`, `test_work_item_link_task.py`) and were READ at pin but not executed in-lane (no provisioned Django deps); probes cite test symbols + asserted behavior.

## Full view (memory graph)
Revalidate `plane` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. Adversarial-retrieval notes: generic queries like "realtime collaboration server horizontal scaling" miss every pass-1 seam (they surface editor frontend hooks); webhook fan-in is invisible to call-graph traces because enqueue rides `.delay()` — use search_code on `model_activity.delay` or the capsule Retrieve vocabulary.

## Boundaries
Adopt the lifecycle ordering, error-triage ladders, force-close choreography, admin-command envelope, debounce/abort kernel, auth fallback grammar, fail-closed IP classification, pinned-fetch transport, redirect re-validation policy, and webhook triage ladder as portable contracts; adapt the Hocuspocus/Yjs specifics, `@plane/editor` converters, axios service layer, requests/urllib3 adapter hook, DRF serializer idioms, and Celery decorator plumbing to your host stack; omit Plane's product routing (project pages, workspace slugs), Express/decorator controller registration, settings-env plumbing (`WEBHOOK_ALLOWED_*`), and the pdf-export Effect-ts pipeline until a named pass mines it.
