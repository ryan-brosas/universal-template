<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->

# Flask: micro-framework foundation (WSGI request lifecycle)

## Use this for
Use when porting Flask's request lifecycle, blueprint registration, session/cookie machinery, config loading, or context/proxy architecture into another framework or a WSGI-compatible reimplementation. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./merged-context-lifecycle.md` — how ONE AppContext serves app+request work; push/pop once-semantics.
- `./contextvar-global-proxies.md` — five LocalProxies over one ContextVar; exact unbound conditions.
- `./wsgi-app-pipeline.md` — wsgi_app ordering: push → dispatch → send → pop(error) in finally.
- `./dispatch-pipeline.md` — full_dispatch tiers: preprocess short-circuit, HTTP/user/unhandled exception classification.
- `./make-response-ladder.md` — legal view return shapes; 2-tuple status-vs-headers disambiguation.
- `./add-url-rule-contract.md` — methods ladder, automatic-OPTIONS decision, endpoint collision assert.
- `./blueprint-deferred-registration.md` — record/replay, dotted names, nested prefix/subdomain composition.
- `./error-handler-lookup.md` — registration key normalization + code→scope→MRO precedence.
- `./stream-with-context-priming.md` — prime-to-sentinel trick keeping ctx alive during streaming.
- `./copy-request-context.md` — per-worker context copies for background threads.
- `./after-this-request.md` — one-shot response hooks stored on the context.
- `./teardown-error-collection.md` — _CollectErrors runs ALL teardowns then raises ExceptionGroup.
- `./config-loading.md` — uppercase filter, JSON-best-effort env vars, `__` nesting.
- `./secure-cookie-session-fsm.md` — open/save decision tree incl. Vary bookkeeping and key rotation.
- `./tagged-json-serializer.md` — lossless non-JSON typing via leading-space tags + trailing-`__` escape.
- `./json-provider.md` — swappable JSON ops; debug-aware compact formatting with unconditional trailing newline.
- `./dispatching-jinja-loader.md` — app-first template precedence; caller-context-wins rule.
- `./class-based-views.md` — as_view closure factory, init policy, MethodView auto-methods.
- `./cli-app-discovery.md` — discovery ladder plus wrong-args factory frame detection.
- `./test-client-context-preservation.md` — environ-injected preserve hook + ExitStack discipline.
- `./debug-request-diagnostics.md` — enctype class-swap trap; body-dropping redirect AssertionError.
- `./wrappers-limits-and-blueprints.md` — per-request limit overrides; innermost-first blueprint paths.
- `./static-route-weakref.md` — weakref view avoids app reference cycle (#3761).
- `./url-adapter-urlfor.md` — trusted-host-at-bind; _external/_scheme defaults in vs out of requests.
- `./flash-messages.md` — explicit key re-write; one-consumption-per-context cache.
- `./logging-and-paths.md` — lazy logger configuration; root/instance path resolution ladders.
- `./subclass-signature-migration.md` — dual-direction add_ctx/remove_ctx shims for old overrides.
- `./sansio-layer-discipline.md` — the no-IO/no-globals layering contract defining the porting seam.

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
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
Flask (BSD-3-Clause), `main@d318b683471101618febed18996405ad26462110`; Codebase Memory project `ext-flask` (FULL mode @ d318b68 = head = base, 2,048n/8,490e, indexed 2026-08-23, generation_matches=true; parse_partial limited to example templates/SQL — none cited).

## Full view (memory graph)
Revalidate `ext-flask` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Graph root /mnt/hdd/utopia/inspo/external/flask, branch main @ d318b6834711 (=head=base, zero drift), FULL mode, nodes 2,048 / edges 8,490; exclusions by design only (.git, docs images); all 29 cited source paths returned no_recorded_issue + metadata_match. Source and direct tests decide shipped claims.

## Boundaries
Adopt the pure contracts: context push/pop semantics, hook ordering, lookup precedence, serializer grammar. Adapt transport integration (WSGI call shape, click CLI, itsdangerous cookies) to your host. Omit product surfaces: dev-server `run()`, dotenv loading, docs/benchmarks/examples trees.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`add-url-rule-contract.md`](./add-url-rule-contract.md)
- [`after-this-request.md`](./after-this-request.md)
- [`blueprint-deferred-registration.md`](./blueprint-deferred-registration.md)
- [`class-based-views.md`](./class-based-views.md)
- [`cli-app-discovery.md`](./cli-app-discovery.md)
- [`config-loading.md`](./config-loading.md)
- [`contextvar-global-proxies.md`](./contextvar-global-proxies.md)
- [`copy-request-context.md`](./copy-request-context.md)
- [`debug-request-diagnostics.md`](./debug-request-diagnostics.md)
- [`dispatch-pipeline.md`](./dispatch-pipeline.md)
- [`dispatching-jinja-loader.md`](./dispatching-jinja-loader.md)
- [`error-handler-lookup.md`](./error-handler-lookup.md)
- [`flash-messages.md`](./flash-messages.md)
- [`json-provider.md`](./json-provider.md)
- [`logging-and-paths.md`](./logging-and-paths.md)
- [`make-response-ladder.md`](./make-response-ladder.md)
- [`merged-context-lifecycle.md`](./merged-context-lifecycle.md)
- [`sansio-layer-discipline.md`](./sansio-layer-discipline.md)
- [`secure-cookie-session-fsm.md`](./secure-cookie-session-fsm.md)
- [`static-route-weakref.md`](./static-route-weakref.md)
- [`stream-with-context-priming.md`](./stream-with-context-priming.md)
- [`subclass-signature-migration.md`](./subclass-signature-migration.md)
- [`tagged-json-serializer.md`](./tagged-json-serializer.md)
- [`teardown-error-collection.md`](./teardown-error-collection.md)
- [`test-client-context-preservation.md`](./test-client-context-preservation.md)
- [`url-adapter-urlfor.md`](./url-adapter-urlfor.md)
- [`wrappers-limits-and-blueprints.md`](./wrappers-limits-and-blueprints.md)
- [`wsgi-app-pipeline.md`](./wsgi-app-pipeline.md)
