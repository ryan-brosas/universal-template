---
name: superset-foundation
description: "Use when porting Apache Superset's chart-data acquisition kernel (per-query cache-key composition under security context, cache fault-tolerance ladders, contribution-totals two-phase sync, annotation-data co-caching, cache-timeout precedence, grouping-sets emulation), its chart-data HTTP entry plane (sync/async job gate with identity-carrying submission, opaque-key cache replay with novel-SQL skip, annotation-layer permission gating, override-before-reauthorization, authorize-before-render ordering), or its Alerts & Reports execution plane (crontab-keyed state machine, WORKING concurrency guard, audit-log row promotion, retry/backoff ladder with window anchors, error-notification grace dedup, webhook SSRF peer validation and response containment). Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."
---
# Superset: chart-data execution & alerts/reports scheduling foundation

## Use this for
Use when porting Apache Superset's chart-data acquisition kernel (per-query cache-key composition under security context, cache fault-tolerance ladders, contribution-totals two-phase sync, annotation-data co-caching, cache-timeout precedence, grouping-sets emulation), its chart-data HTTP entry plane (sync/async job gate with identity-carrying submission, opaque-key cache replay with novel-SQL skip, annotation-layer permission gating, override-before-reauthorization, authorize-before-render ordering), or its Alerts & Reports execution plane (crontab-keyed state machine, WORKING concurrency guard, audit-log row promotion, retry/backoff ladder with window anchors, error-notification grace dedup, webhook SSRF peer validation and response containment). Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/df-payload-acquisition-ladder.md` — how one query acquires its dataframe payload with timing kept outside the payload.
- `references/stale-cache-shape-miss-downgrade.md` — when a loaded cache entry is deliberately demoted to a miss.
- `references/query-cache-manager-fault-tolerance.md` — backend-outage-to-miss fall-through, force_cached failure, and never-cache-failure gating.
- `references/annotation-cache-context-binding.md` — binding co-cached annotation data to requesting user and per-source RLS.
- `references/contribution-totals-two-phase-sync.md` — totals-query detection, injection, and cache_values re-sync.
- `references/cache-key-contribution-exclusion.md` — QueryObject.cache_key normalization rules that keep keys stable across workers.
- `references/cache-timeout-precedence-ladder.md` — five-step timeout resolution incl. the native-filter-options override trap.
- `references/grouping-sets-emulation-fallback.md` — per-rollup-level fan-out when an engine lacks native GROUPING SETS.
- `references/report-state-machine-dispatch.md` — persisted-last_state keyed selection of exactly one state class; unknown states fail loudly.
- `references/working-state-concurrency-refusal.md` — duplicate-execution guard: timeout recovery vs refused recompute with a side audit row.
- `references/create-log-working-row-promotion.md` — one execution ⇒ one log row via in-place promotion of the WORKING trigger row.
- `references/retry-window-staleness-anchor.md` — crontab-window identity carried through task re-enqueues; stale-window reset and in-flight skip.
- `references/retry-or-error-backoff-ladder.md` — boolean-outcome retry funnel with capped exponential backoff and never-masked originals.
- `references/error-grace-notification-dedup.md` — one owner email per failure streak via marker-row queries that require a success to reset.
- `references/webhook-peer-validation-toctou.md` — resolve-time URL check plus connect-time peer-IP re-validation closing DNS-rebinding TOCTOU.
- `references/webhook-readback-oracle-containment.md` — remote response bodies logged server-side only; raised errors carry status codes, not bytes.
- `references/chart-data-async-job-ladder.md` — four-conjunct sync/async gate, try-cache-first handoff, and identity-carrying job submission for cache-key consistency.
- `references/cache-replay-opaque-key-skip.md` — serving pre-computed results from unguessable cache keys with the novel-SQL check skipped by replay flag.
- `references/annotation-layer-permission-gate.md` — annotation read permission enforced before any layer lookup; typed missing-id errors.
- `references/viz-annotation-override-injection.md` — chart-as-annotation overrides applied before re-authorization of the nested execution.
- `references/raise-for-access-before-validate.md` — authorization strictly precedes rendering caller-supplied filter expressions.

## Capsule map
**Chart-data plane**
- **Payload acquisition** — `df-payload-acquisition-ladder`: validate-before-cache-key, force = context.force ∨ CACHE_DISABLED_TIMEOUT, failed validation is recorded but never cached, frozen timing sidecar.
- **Cache compatibility** — `stale-cache-shape-miss-downgrade`: loaded entry missing `applied_filter_columns` while filters exist ⇒ `is_loaded=False`, live requery.
- **Cache fault tolerance** — `query-cache-manager-fault-tolerance`: read outage ⇒ miss; `force_cached` miss ⇒ `CacheLoadError`; set only when `is_loaded ∧ status ≠ FAILED`; BigQuery memory-limit flags ride `flask.g` and the cached value.
- **Annotation security binding** — `annotation-cache-context-binding`: same-entry annotation data forces `{user_id, source_rls}` into the query cache key.
- **Contribution totals** — `contribution-totals-two-phase-sync`: implicit totals query (`columns==[] ∧ metrics ∧ no pp`) gets `row_limit=None`; computed totals injected into each contribution op; `cache_values["queries"]` merged back `{**cached, **to_dict()}`.
- **Key stability** — `cache-key-contribution-exclusion`: pop `contribution_totals` from options for hashing; sort `extra_cache_keys` by `(type name, str)`; drop resolved `from_dttm/to_dttm`; whitelist annotation fields.
- **Timeout precedence** — `cache-timeout-precedence-ladder`: custom → native-filter-options → slice/datasource → DATA_CACHE_CONFIG default → global default.
- **Rollup emulation** — `grouping-sets-emulation-fallback`: one sequential query per level with `row_limit=None`/`row_offset=0`, marker columns, offset applied once post-concat.

**Chart-data HTTP entry plane**
- **Async job gate** — `chart-data-async-job-ladder`: async only when feature flag ∧ JSON ∧ FULL ∧ cache enabled; try `force_cached` first unless forced; validate channel before submit; guest token + `task_id=job_id` keep keys and cancellation consistent.
- **Cache replay** — `cache-replay-opaque-key-skip`: unguessable SHA-256 key + `force_cached` + original-check-already-passed justify skipping the novel-SQL byte check (sanitization rewrites extras pre-cache); access validation still runs.
- **Annotation permission** — `annotation-layer-permission-gate`: `can_read Annotation` checked before any DAO lookup; empty native-layer requests bypass; missing ids ⇒ typed errors; 5-column whitelist projection.
- **Viz annotation overrides** — `viz-annotation-override-injection`: time-grain/time-range overrides mutate the reconstructed context BEFORE `validate()` re-authorizes under the current user; outer `force` propagates; all failures normalize to one exception type.
- **Authorize-before-render** — `raise-for-access-before-validate`: the single `validate()` choke point authorizes first because query validation renders caller-supplied filter expressions; denied callers' input is never rendered.

**Alerts & reports plane**
- **State dispatch** — `report-state-machine-dispatch`: ordered class registry matched against persisted `last_state` (`current_states` ∨ `initial` for None); no match ⇒ `ReportScheduleStateNotFoundError`.
- **Concurrency guard** — `working-state-concurrency-refusal`: WORKING held ⇒ timeout recovers by terminalizing ERROR, otherwise refuse with a distinct audit row (`reuse_working_log=False`) leaving the owner untouched.
- **Audit-row promotion** — `create-log-working-row-promotion`: terminal writes promote this execution's own WORKING trigger row (uuid ∧ state ∧ null-error match); marker rows stay verbatim; StaleDataError ⇒ typed error.
- **Window identity** — `retry-window-staleness-anchor`: original crontab timestamp travels through every re-enqueue; naive/microsecond normalization before anchor comparison; healthy chains suppress new windows, dead chains (older than max delay) don't wedge.
- **Retry funnel** — `retry-or-error-backoff-ladder`: True ⇒ exit cleanly after RETRYING log + capped `min(base·2^n, cap)` countdown re-enqueue; False ⇒ exhausted, counter reset + optional final-failure report; logging failures chain from the original exception.
- **Grace dedup** — `error-grace-notification-dedup`: newest marker row counts only while no non-ERROR/non-WORKING row follows it; marker written only on verified delivery, send failures overwrite it.
- **SSRF TOCTOU** — `webhook-peer-validation-toctou`: URL policy pre-flight + urllib3 connection-class substitution validating the actual socket peer post-connect; pool map replaced wholesale; internal-hosts opt-out bypasses both layers.
- **Response containment** — `webhook-readback-oracle-containment`: 500-char sanitized server-side-only body logs; raised messages carry status codes only; 3xx = unfollowed redirect = failure; backoff retries only 5xx/429.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
Apache Superset (Apache-2.0), `master@9f505eb0cbbc39b78f512765d82fd63cf5ad70e6`; Codebase Memory project `superset` (FULL, ready, 94,640n/464,372e, generation 2026-08-25T20:09:52Z; parse_partial 71 files — helm/jinja/CSS/frontend ranges, none cited). Pass 1: chart-data query execution & caching plane (8 capsules). Pass 2: alerts & reports execution plane (`superset/commands/report/execute.py`, `superset/commands/report/alert.py`, `superset/reports/notifications/webhook.py`, `superset/daos/report.py`; 8 capsules). Pass 3: chart-data HTTP entry plane (`superset/charts/data/api.py`, `superset/commands/chart/data/{get_data_command,create_async_job_command}.py`, `superset/async_events/async_query_manager.py`, `superset/security/manager.py`, annotation plane of `query_context_processor.py`; 5 capsules; Codebase Memory MCP disconnected — direct source+test reading fallback).

## Full view (memory graph)
Revalidate `superset` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt the pure contracts above (acquisition ladder, key composition, timeout precedence, fallback fan-out; async gate + identity-carrying submission, opaque-key replay skip, check-before-lookup permission gating, override-then-reauthorize, authorize-before-render; state dispatch, row promotion, retry/window ladders, grace dedup, SSRF peer validation, response containment); adapt Flask/`current_app.config`, `security_manager`, DAO, SQLAlchemy session, and pandas-frame plumbing to your host; omit Superset's REST envelope, stats-logger counter names, BigQuery-specific `g.bq_memory_limited` provenance, Celery `apply_async`/soft-limit mechanics, Slack/SlackV2 transports, and the frontend query-context serialization.
