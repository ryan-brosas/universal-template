<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->


# Django: HTTP-core foundations

## Use this for
Use when building or porting a Python web framework core: dual-mode (sync/async) middleware dispatch, ASGI/WSGI server bridges, URL routing with converters and namespaces, request-body lifecycle guards, or response/cookie encoding contracts. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./middleware-mode-adaptive-chain.md` — where sync↔async adapters install in the middleware onion and what decides each hop's mode.
- `./hook-side-tables.md` — process_view/process_template_response/process_exception execution order outside the onion.
- `./exception-conversion-per-hop.md` — per-hop exception→response conversion and the 403/400/404/500 classification ladder.
- `./asgi-disconnect-race.md` — TaskGroup race between response delivery and client disconnect with sentinel-exception success signalling.
- `./asgi-header-funnel.md` — scope-bytes→META decoding with underscore-spoofing rejection and duplicate-header join rules.
- `./asgi-body-spool.md` — SpooledTemporaryFile body buffering with per-chunk roll detection and per-request thread sensitivity.
- `./asgi-response-send.md` — http.response.start/body framing, cookie headerization, and aclosing(aiter()) stream consumption.
- `./wsgi-environ-decoding.md` — latin1 environ byte-recovery and mod_rewrite SCRIPT_NAME reconstruction ladder.
- `./wsgi-file-wrapper-close.md` — close-delegation patch so platform-managed file bodies still release resources.
- `./urlresolvers-resolve-tried.md` — depth-first first-wins resolution, kwargs merge order, and the tried-path 404 ledger.
- `./routepattern-fast-path.md` — path() grammar compile, converter two-way contract, and fall-through on to_python ValueError.
- `./reverse-populate-namespaces.md` — reversed-order reverse-dict population, re-entrancy latch, and namespace walking in reverse().
- `./body-single-consumption.md` — _read_started latch plus the declared-then-actual size gate for DATA_UPLOAD limits.
- `./host-validation-ladder.md` — grammar-first ALLOWED_HOSTS validation against X-Forwarded-Host spoofing.
- `./response-header-cookie-lifecycle.md` — set-time charset/newline enforcement and prefix-aware delete_cookie.
- `./streaming-dual-mode.md` — iterator-kind latching with buffered cross-mode sync↔async consumption bridges.

## Capsule map
- **Middleware engine** — `middleware-mode-adaptive-chain`: capability-negotiated per-hop adaptation; adapters only at genuine mode boundaries; process_exception pinned sync.
- **Middleware engine** — `hook-side-tables`: view hooks run declaration-order pre-view; exception/template-response tables run reverse-order around `_get_response`.
- **Middleware engine** — `exception-conversion-per-hop`: every chain hop wrapped so callees always receive responses; SuspiciousOperation family poisons POST cache then logs to `django.security.*`.
- **ASGI bridge** — `asgi-disconnect-race`: raise-to-win TaskGroup race; singleton ExceptionGroup unwrapping preserves original tracebacks.
- **ASGI bridge** — `asgi-header-funnel`: underscore names dropped pre-normalization; cookies "; "-joined, others ","-joined; duplicate Content-Length tolerated downstream.
- **ASGI bridge** — `asgi-body-spool`: spool rolls at FILE_UPLOAD_MAX_MEMORY_SIZE; rolled writes go thread-insensitive off-loop; disconnect closes spool before aborting.
- **ASGI bridge** — `asgi-response-send`: one start message, chunked bodies, explicit empty closing body message; FileResponse block_size promoted to chunk_size.
- **WSGI bridge** — `wsgi-environ-decoding`: iso-8859-1 round-trip on every environ read; SCRIPT_URL/REDIRECT_URL minus PATH_INFO recovers rewritten script names.
- **WSGI bridge** — `wsgi-file-wrapper-close`: patch file_to_stream.close to response.close before handing the server its wrapper.
- **URL routing** — `urlresolvers-resolve-tried`: ordered depth-first match, inner-wins kwargs merge, positional args dropped when any named group exists anywhere.
- **URL routing** — `routepattern-fast-path`: converter-free endpoints match by string equality; converter ValueError fails the route, not the request.
- **URL routing** — `reverse-populate-namespaces`: last-registered name wins lookups; per-thread populating latch; current_app selects instance namespaces.
- **Request primitives** — `body-single-consumption`: exception-enforced single read; size gated on declared Content-Length AND seekable actual size.
- **Request primitives** — `host-validation-ladder`: strict fullmatch grammar precedes allowlist; invalid hosts yield empty domain and DisallowedHost.
- **Response primitives** — `response-header-cookie-lifecycle`: ascii keys / latin-1 values validated at set time; deletes force secure for __Secure-/__Host-/SameSite=none.
- **Response primitives** — `streaming-dual-mode`: iterator kind latched at assignment; wrong-protocol consumption buffers whole content via async_to_sync/sync_to_async.

## Extending the foundation
Add one `./<seam>.md` capsule-v2 for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
django (BSD-3-Clause), `main@03988c5a5ba248c3b9b11ea96fd4fda5e98849aa`; Codebase Memory project `ext-django` (FULL mode, 55,458 nodes / 344,587 edges, head==base zero drift at citation time; parse_partial limited to CSS/HTML templates, none cited).

## Full view (memory graph)
Revalidate `ext-django` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt the pure contracts: mode-adaptive chain building, per-hop exception conversion, resolver ordering semantics, single-consumption body gates, set-time header validation. Adapt the host-specific integrations: asgiref adapters, ThreadSensitiveContext, Django settings access, SimpleCookie serialization. Omit Django-specific transport/product behavior: signals framework internals, DEBUG technical pages, ATOMIC_REQUESTS transaction wiring, contrib apps, template engine.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`asgi-body-spool.md`](./asgi-body-spool.md)
- [`asgi-disconnect-race.md`](./asgi-disconnect-race.md)
- [`asgi-header-funnel.md`](./asgi-header-funnel.md)
- [`asgi-response-send.md`](./asgi-response-send.md)
- [`body-single-consumption.md`](./body-single-consumption.md)
- [`exception-conversion-per-hop.md`](./exception-conversion-per-hop.md)
- [`hook-side-tables.md`](./hook-side-tables.md)
- [`host-validation-ladder.md`](./host-validation-ladder.md)
- [`middleware-mode-adaptive-chain.md`](./middleware-mode-adaptive-chain.md)
- [`response-header-cookie-lifecycle.md`](./response-header-cookie-lifecycle.md)
- [`reverse-populate-namespaces.md`](./reverse-populate-namespaces.md)
- [`routepattern-fast-path.md`](./routepattern-fast-path.md)
- [`streaming-dual-mode.md`](./streaming-dual-mode.md)
- [`urlresolvers-resolve-tried.md`](./urlresolvers-resolve-tried.md)
- [`wsgi-environ-decoding.md`](./wsgi-environ-decoding.md)
- [`wsgi-file-wrapper-close.md`](./wsgi-file-wrapper-close.md)
