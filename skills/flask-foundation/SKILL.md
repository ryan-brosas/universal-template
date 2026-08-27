---
name: flask-foundation
description: "Use when porting Flask's micro-framework (WSGI request lifecycle) — blueprint registration, session/cookie machinery, config loading, or context/proxy architecture — into another framework or a WSGI-compatible reimplementation. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."
---
# Flask: micro-framework foundation (WSGI request lifecycle)

## Use this for
Use when porting Flask's request lifecycle, blueprint registration, session/cookie machinery, config loading, or context/proxy architecture into another framework or a WSGI-compatible reimplementation. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/merged-context-lifecycle.md` — how ONE AppContext serves app+request work; push/pop once-semantics.
- `references/contextvar-global-proxies.md` — five LocalProxies over one ContextVar; exact unbound conditions.
- `references/wsgi-app-pipeline.md` — wsgi_app ordering: push → dispatch → send → pop(error) in finally.
- `references/dispatch-pipeline.md` — full_dispatch tiers: preprocess short-circuit, HTTP/user/unhandled exception classification.
- `references/make-response-ladder.md` — legal view return shapes; 2-tuple status-vs-headers disambiguation.
- `references/add-url-rule-contract.md` — methods ladder, automatic-OPTIONS decision, endpoint collision assert.
- `references/blueprint-deferred-registration.md` — record/replay, dotted names, nested prefix/subdomain composition.
- `references/error-handler-lookup.md` — registration key normalization + code→scope→MRO precedence.
- `references/stream-with-context-priming.md` — prime-to-sentinel trick keeping ctx alive during streaming.
- `references/copy-request-context.md` — per-worker context copies for background threads.
- `references/after-this-request.md` — one-shot response hooks stored on the context.
- `references/teardown-error-collection.md` — _CollectErrors runs ALL teardowns then raises ExceptionGroup.
- `references/config-loading.md` — uppercase filter, JSON-best-effort env vars, `__` nesting.
- `references/secure-cookie-session-fsm.md` — open/save decision tree incl. Vary bookkeeping and key rotation.
- `references/tagged-json-serializer.md` — lossless non-JSON typing via leading-space tags + trailing-`__` escape.
- `references/json-provider.md` — swappable JSON ops; debug-aware compact formatting with unconditional trailing newline.
- `references/dispatching-jinja-loader.md` — app-first template precedence; caller-context-wins rule.
- `references/class-based-views.md` — as_view closure factory, init policy, MethodView auto-methods.
- `references/cli-app-discovery.md` — discovery ladder plus wrong-args factory frame detection.
- `references/test-client-context-preservation.md` — environ-injected preserve hook + ExitStack discipline.
- `references/debug-request-diagnostics.md` — enctype class-swap trap; body-dropping redirect AssertionError.
- `references/wrappers-limits-and-blueprints.md` — per-request limit overrides; innermost-first blueprint paths.
- `references/static-route-weakref.md` — weakref view avoids app reference cycle (#3761).
- `references/url-adapter-urlfor.md` — trusted-host-at-bind; _external/_scheme defaults in vs out of requests.
- `references/flash-messages.md` — explicit key re-write; one-consumption-per-context cache.
- `references/logging-and-paths.md` — lazy logger configuration; root/instance path resolution ladders.
- `references/subclass-signature-migration.md` — dual-direction add_ctx/remove_ctx shims for old overrides.
- `references/sansio-layer-discipline.md` — the no-IO/no-globals layering contract defining the porting seam.

## Capsule map
- **Context kernel** — `merged-context-lifecycle`, `contextvar-global-proxies`: one ContextVar, one merged context, count-latched push/pop.
- **WSGI pipeline** — `wsgi-app-pipeline`, `dispatch-pipeline`, `make-response-ladder`: environ→response with three-tier error handling and return-value conversion.
- **Routing surface** — `add-url-rule-contract`, `static-route-weakref`, `url-adapter-urlfor`: rule/methods/OPTIONS registration, leak-free static views, adapter binding with host trust.
- **Blueprint system** — `blueprint-deferred-registration`: closures replayed at register time under composed dotted names/prefixes.
- **Hooks & errors** — `error-handler-lookup`, `teardown-error-collection`, `after-this-request`, `debug-request-diagnostics`: precedence ladders that decide which user code runs when.
- **Streaming & background** — `stream-with-context-priming`, `copy-request-context`: keeping contexts alive past dispatch.
- **State & serialization** — `secure-cookie-session-fsm`, `tagged-json-serializer`, `json-provider`, `flash-messages`, `config-loading`: cookie FSM over tagged JSON behind a swappable provider.
- **Templates** — `dispatching-jinja-loader`: app-first loader chain with original-context precedence.
- **Views** — `class-based-views`: function-factory CBVs with auto method tables.
- **Request/Response objects** — `wrappers-limits-and-blueprints`: per-request limit overrides and innermost-first blueprint paths.
- **Tooling** — `cli-app-discovery`, `test-client-context-preservation`, `logging-and-paths`: app discovery, preserved test contexts, lazy logging.
- **Evolution seams** — `subclass-signature-migration`, `sansio-layer-discipline`: API migration shims and the async-port boundary.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
Flask (BSD-3-Clause), `main@d318b683471101618febed18996405ad26462110`; Codebase Memory project `ext-flask` (FULL mode @ d318b68 = head = base, 2,048n/8,490e, indexed 2026-08-23, generation_matches=true; parse_partial limited to example templates/SQL — none cited).

## Full view (memory graph)
Revalidate `ext-flask` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Graph root /mnt/hdd/utopia/inspo/external/flask, branch main @ d318b6834711 (=head=base, zero drift), FULL mode, nodes 2,048 / edges 8,490; exclusions by design only (.git, docs images); all 29 cited source paths returned no_recorded_issue + metadata_match. Source and direct tests decide shipped claims.

## Boundaries
Adopt the pure contracts: context push/pop semantics, hook ordering, lookup precedence, serializer grammar. Adapt transport integration (WSGI call shape, click CLI, itsdangerous cookies) to your host. Omit product surfaces: dev-server `run()`, dotenv loading, docs/benchmarks/examples trees.
