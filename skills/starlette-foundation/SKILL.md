---
name: starlette-foundation
description: "Use when porting Starlette's ASGI kernel — the router match loop and `{param:convertor}` path grammar, mount child-scope rewriting (`root_path`/`app_root_path`), lifespan state machine, exception-handler plumbing with response-started latching, `BaseHTTPMiddleware`'s memory-stream bridge, single-consumption request body/form contracts, multipart callback state machine, streaming disconnect ladder + Range/multipart-byteranges engine, WebSocket dual state machines, signed-cookie sessions, static-file containment, CORS preflight algebra, scope-data plane (ImmutableMultiDict/MultiDict/QueryParams/FormData repeated-key algebra, Headers first-match byte store vs MutableHeaders live-list kernel, lifespan↔request State write-through), URL construction/mutation plane (tri-form constructor with lazy SplitResult cache, replace() netloc reassembly with IPv6 guard), HTTPConnection derivation plane (identity-equality Mapping façade, snapshot memoization ladder, assert-guided session/auth/user facades, client Address)"
disable-model-invocation: true
---
# Starlette: Python ASGI toolkit foundation

## Use this for
Use when porting Starlette's ASGI kernel — the router match loop and `{param:convertor}` path grammar, mount child-scope rewriting (`root_path`/`app_root_path`), lifespan state machine, exception-handler plumbing with response-started latching, `BaseHTTPMiddleware`'s memory-stream bridge, single-consumption request body/form contracts, multipart callback state machine, streaming disconnect ladder + Range/multipart-byteranges engine, WebSocket dual state machines, signed-cookie sessions, static-file containment, CORS preflight algebra, the scope-data plane (ImmutableMultiDict/MultiDict/QueryParams/FormData repeated-key algebra, Headers first-match byte store vs MutableHeaders live-list kernel, lifespan↔request State write-through), the URL construction/mutation plane (tri-form constructor with lazy SplitResult cache, replace() netloc reassembly with IPv6 guard), or the HTTPConnection derivation plane (identity-equality Mapping façade, snapshot memoization ladder, assert-guided session/auth/user facades, client Address) — into another framework or service. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/router-match-loop.md` — full-then-partial two-pass dispatch; slash-redirect re-match; raise-vs-return 404 duality.
- `references/path-convertor-grammar.md` — template→named-group compilation, five built-in convertors as two-way contracts, reversal round-trip guarantees.
- `references/mount-child-scope.md` — root_path accumulation, write-once app_root_path, conservative get_route_path stripping ladder.
- `references/lifespan-state-machine.md` — startup/shutdown message exchange, started-latch failure mapping, four-shape lifespan normalization.
- `references/endpoint-adapter-threadpool.md` — sync endpoints via threadpool partials; wrapper-at-route-level exception scoping; class-vs-function classification.
- `references/exception-handler-plumbing.md` — MRO lookup over scope-injected tables, response-started RuntimeError, always-re-raise outer 500 middleware.
- `references/middleware-stack-order.md` — ServerError…user…Exception sentinel sandwich, reversed-fold composition at app/router/route levels, lazy build.
- `references/base-http-middleware-bridge.md` — _CachedRequest replay FSM, call_next stream dance, EndOfStream context scrubbing, exception-once latch.
- `references/request-body-form-contract.md` — stream/body/json interplay, trailing empty chunk, form content-type gate with 400 promotion.
- `references/multipart-parser-callbacks.md` — per-chunk write/finish queues bridging sync callbacks to async file IO; close-on-error tempfile ledger.
- `references/response-headers-cookies.md` — content-length/content-type population suppression matrix, multi-entry Set-Cookie appending, WS denial shim.
- `references/streaming-range-engine.md` — ASGI spec-version strategy switch, full Range decision tree, multipart-byteranges length precomputation.
- `references/url-scope-reconstruction.md` — Host-header trust gate via `_HOST_RE`, URLPath protocol-aware joining, raw-bytes-pairs header store.
- `references/websocket-state-machines.md` — client_state vs application_state legality tables, OSError→1006 conversion, denial-response extension gate.
- `references/staticfiles-containment.md` — double-realpath commonpath escape guard, error-to-status mapping, If-None-Match precedence + 304 header whitelist.
- `references/gzip-responder-split.md` — defer-until-response-start decisions, streaming Z_SYNC_FLUSH, dedicated CapacityLimiter for large chunks.
- `references/cors-header-algebra.md` — preflight headers computed once at init; credentials force origin mirroring paired with Vary.
- `references/session-signed-cookies.md` — accessed/modified dict tracking driving set/expire/no-op cookie lifecycle three-way.
- `references/body-limit-nesting.md` — one shared byte counter adopted-or-tightened by nested limit layers via scope keys.
- `references/class-endpoint-dispatch.md` — method table at init, HEAD→GET fallback, WS close-code ledger through finally.
- `references/config-environ-guard.md` — Environ refuses writes after reads; sentinel-default typed config with cast-everything.
- `references/auth-scope-decorator.md` — signature-scan connection discovery, redirect-vs-403 failure ladder, anonymous-not-error backend contract.
- `references/testclient-portal-bridge.md` — blocking portal over async ASGI, upgrade-exception WS sessions, lifespan context manager with state sharing.
- `references/collapsing-taskgroup-threadpool.md` — single-exception ExceptionGroup unwrapping; StopIteration coercion across the threadpool boundary.
- `references/uploadfile-spool-awareness.md` — roll prediction deciding inline vs threadpool IO from SpooledTemporaryFile internals.
- `references/background-task-chain.md` — post-final-message sequential execution, construction-time async detection, first-error-stops-chain.
- `references/wsgi-thread-bridge.md` — worker-thread WSGI callable feeding a memory stream; exc_info as error signal (deprecated upstream).
- `references/otel-route-late-naming.md` — span renamed from `scope["route"]` in finally; re-entrancy flag for nested apps; no-op provider bypass.
- `references/schema-route-walk.md` — recursive Mount/Host endpoint enumeration, converter stripping, docstring-after-`---` YAML contract.
- `references/templates-debug-channel.md` — pass_context url_for global, request setdefault ordering, http.response.debug emission.
- `references/redirect-middlewares.md` — TrustedHost wildcard grammar + www redirect; HTTPSRedirect 307 port normalization.
- `references/multidict-dual-representation.md` — `_dict` last-wins vs `_list` ordered-all; getlist split API; class-exact multiplicity equality.
- `references/multidict-mutation-rebalance.md` — filter-rewrite mutation kernel; setlist moves-to-end; empty-setlist==pop; self-update identity.
- `references/queryparams-roundtrip-contract.md` — parse_qsl keep_blank_values → urlencode(_list) lossless loop; latin-1 bytes; str coercion.
- `references/state-scope-write-through.md` — one-dict façade; lifespan merge-before-startup-complete; app.state deliberately separate; shallow-share leak rule.
- `references/masked-repr-hygiene.md` — Secret full-mask repr + bool delegation + str-at-use; URL password-only repr mask.
- `references/headers-first-match-byte-store.md` — latin-1 byte rows; first-match reads (vs multi-dict last-wins); non-deduping views; scope-aliasing constructor.
- `references/mutableheaders-live-list.md` — replace-in-place setitem keeps position; append preserves duplicates; raw LIVE list aliasing to the ASGI start message; FileResponse copy discipline.
- `references/url-tri-form-constructor.md` — mutually exclusive url/scope/**components forms; lazy SplitResult cache; `__str__` returns original bytes verbatim; string equality.
- `references/url-replace-netloc-reassembly.md` — authority-touching replace rebuilds netloc by hand; IPv6 bracket guard; unspecified components preserved via current-value defaults.
- `references/connection-mapping-identity-facade.md` — Mapping-over-scope delegation with `__eq__ = object.__eq__`; connections never structurally equal.
- `references/connection-derived-property-memoization.md` — hasattr-guarded compute-once views (url/base_url/headers/query_params/cookies); snapshot-at-first-access semantics; state as live alias exception.
- `references/assert-guided-stack-facades.md` — session/auth/user assert messages naming the missing middleware; duck-typed mark_accessed hook feeding Vary: Cookie.
- `references/client-address-namedtuple.md` — get-lenient scope read; None-preserving absence; NamedTuple tuple+attribute dual ergonomics.

## Capsule map
- **Routing core** — `router-match-loop`: two-pass FULL/PARTIAL dispatch; `path-convertor-grammar`: typed path params both directions; `mount-child-scope`: prefix delegation with root_path surgery; `endpoint-adapter-threadpool`: func/class → ASGI adapters.
- **App lifecycle** — `lifespan-state-machine`: ASGI lifespan message protocol; `middleware-stack-order`: sentinel onion + reversed fold; `class-endpoint-dispatch`: verb tables + WS hooks; `background-task-chain`: post-response task execution.
- **Errors** — `exception-handler-plumbing`: status/class handler lookup, started-latch, outer re-raise net.
- **HTTP middleware** — `base-http-middleware-bridge`: Request/Response façade over raw ASGI; `gzip-responder-split`: deferred compression decisions; `cors-header-algebra`: precomputed policy headers; `session-signed-cookies`: client-side session cookie lifecycle; `body-limit-nesting`: layered quota coordination; `auth-scope-decorator`: endpoint-level scope gates; `redirect-middlewares`: host/scheme redirects; `otel-route-late-naming`: telemetry spans named after routing.
- **Response plane** — `response-headers-cookies`: header population rules + cookies; `streaming-range-engine`: disconnect handling + Range engine; `headers-first-match-byte-store` + `mutableheaders-live-list`: immutable view vs live mutable header kernel.
- **Data & URLs** — `url-scope-reconstruction`: trusted URL building from scope primitives; `url-tri-form-constructor` + `url-replace-netloc-reassembly`: URL construction forms and component mutation with IPv6-safe netloc reassembly; `multidict-dual-representation` + `multidict-mutation-rebalance`: repeated-key read/mutation algebra; `queryparams-roundtrip-contract`: lossless query-string loop; `masked-repr-hygiene`: Secret/URL credential masking.
- **Request plane** — `request-body-form-contract`: one-consumption body/stream/form; `multipart-parser-callbacks`: async bridge over python-multipart callbacks; `uploadfile-spool-awareness`: roll-predicted file IO; `config-environ-guard`: read-frozen env access; `state-scope-write-through`: lifespan↔request state sharing (app.state separate); `connection-mapping-identity-facade` + `connection-derived-property-memoization`: scope façade identity equality + snapshot-at-first-access derivation ladder; `assert-guided-stack-facades`: middleware-named assert failures for session/auth/user; `client-address-namedtuple`: None-preserving peer address.
- **Realtime** — `websocket-state-machines`: dual FSMs for WS message legality.
- **Static files** — `staticfiles-containment`: traversal-proof lookup + conditional GET.
- **Schema & templates** — `schema-route-walk`: routes → OpenAPI entries; `templates-debug-channel`: Jinja integration + test introspection channel.
- **Test infrastructure** — `testclient-portal-bridge`: sync test client over async apps.
- **Async kernels** — `collapsing-taskgroup-threadpool`: ExceptionGroup collapse + StopIteration coercion; `wsgi-thread-bridge`: legacy sync-app bridge pattern.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
Starlette (BSD-3-Clause), `main@675ae76855d3d09f5a4493c15ad321a3cd02390d`; Codebase Memory project `starlette` — REINDEXED under the short name 2026-08-26 (prior graph name `ext-starlette` is dead from the MCP registry; same HEAD/pin, ready FULL, 2,661 nodes / 13,843 edges, generation 2026-08-25T19:58:45Z; parse_partial=1 docs-only `docs/overrides/partials/toc-item.html`, skipped=0). Prior passes produced 31 refs (history in earlier leaf provenance); pass 2026-08-26 (FAC-266) added the 7 scope-data-plane capsules; pass 2 of 2026-08-26 (FAC-266 deep pass) added the 6 connection/URL derivation-plane capsules — all cited paths (datastructures.py, requests.py, middleware/sessions.py, test_datastructures.py, test_requests.py) check_index_coverage `no_recorded_issue`, generation-matched.

## Full view (memory graph)
Revalidate `starlette` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. Earlier verification at the same pin: 77/78 cited symbols resolved line-exact via search_graph name_pattern (`call_next` is a closure — retrieve via `wrapped_receive`/`_StreamingResponse`); adversarial retrieval against wrong projects returned zero hits for these seam names. Pass-2 re-verification: upstream pytest executed at pin — tests/test_datastructures.py 38 passed + 7-test state subset passed; `get_code_snippet` served source byte-equal to direct reads for ImmutableMultiDict (:253-319) and State (:664-704); trace_path confirmed consumer edges State←{Starlette.__init__, HTTPConnection.state}, QueryParams←HTTPConnection.query_params, MutableHeaders←{CORS, gzip, sessions, FileResponse, Response.headers}. Pass-3 verification (same pin, zero drift): CommaSeparatedStrings consumer sweep proved ZERO production callers (trace_path inbound=0; search_code full-repo = own test + docs only) — stays uncited by evidence; decisive direct reads datastructures.py :1-175 and requests.py :73-207 back the six new derivation-plane capsules; coverage caveats recorded inside capsules where no direct test exists (identity __eq__, assert messages, **components constructor form).

## Boundaries
Adopt the pure contracts: match-loop ordering, convertor two-way round trips, child-scope key writes, lifespan message protocol, exception lookup + started-latch, one-consumption body semantics, range parsing ladder, WebSocket FSMs, containment realpath gate, collapsing task group, read-frozen environ. Adapt host-specific integration: anyio stream/limiter plumbing, itsdangerous signing, Jinja2 globals, python-multipart callback glue, SpooledTemporaryFile internals. Omit product/deprecated surface: WSGI middleware (upstream points to a2wsgi), generator lifespans (deprecated), push promises (HTTP/2 server-push era), run_until_first_complete (deprecated), docs/benchmarks fixtures.
