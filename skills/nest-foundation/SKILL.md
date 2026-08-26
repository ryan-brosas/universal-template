---
name: nest-foundation
description: "Use when building or porting a DI container, module system, provider lifecycle, bootstrap pipeline, request-scoped injection, route registration/URL composition, validation pipes, or a boot log buffer — NestJS's core injector + router + pipe kernel as source-confirmed contracts."
disable-model-invocation: true
---
# nest: Dependency-injection container, router & pipe foundation

## Use this for
Use when implementing a DI/IoC container (module graph, provider resolution, scopes), a framework bootstrap/lifecycle pipeline (init/destroy/shutdown hooks), request-scoped injection, lazy module loading, test-oriented module overrides, route-path composition/versioning/specificity ordering, argument validation & coercion pipes, or boot-time log buffering. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/opaque-module-tokens.md` — how module instances dedupe by symbol-cached opaque token instead of class identity.
- `references/container-registration.md` — token-keyed addModule/addProvider contract with distance-pinned globals.
- `references/module-record.md` — what a Module owns: five collections plus implicit self/ModuleRef/config providers.
- `references/instance-wrapper.md` — dual-keyed instance cache (contextId × transient inquirer) with lazy prototype-shell clones.
- `references/constructor-resolution.md` — concurrent ctor-param resolution gated by an all-participants Barrier.
- `references/settlement-signal.md` — pending/join protocol that makes concurrent loads safe and detects cycles.
- `references/provider-lookup-ladder.md` — self → imports visibility ladder with first-export-match-wins.
- `references/forwardref-resolution.md` — circular-import survival via thunk unwrap + deferred load + prototype merge.
- `references/dependency-tree-introspection.md` — memoized static/durable subtree analysis with ancestor-fan-in invalidation.
- `references/transient-isolation.md` — effective-inquirer re-keying so nested transients never share instances.
- `references/bootstrap-pipeline.md` — scan-all → instantiate-all → apply-globals inside one ExceptionsZone boundary.
- `references/metadata-scanning.md` — decorator-metadata to container records, incl. APP_* UUID-token rewire + deferred apply.
- `references/prototype-prepass.md` — two-pass instantiation: shell prototypes for all wrappers before any constructor runs.
- `references/internal-core-module.md` — hidden global module exposing REQUEST/INQUIRER/Reflector via container-closure factories.
- `references/lazy-module-loading.md` — post-boot modules via scoped re-run of the standard scan+instantiate pipeline.
- `references/lifecycle-hooks.md` — distance-descending init order, per-level fan-out, exact reversal for teardown.
- `references/instance-links.md` — flattened token→links index powering get()/resolve() with strict/non-strict semantics.
- `references/handler-composition.md` — the guards→interceptors→pipes→handler→filter onion built once per route.
- `references/barrier-primitive.md` — 55-line rendezvous primitive; zero-count fast path and unconditional error signaling.
- `references/error-enrichment.md` — context-carrying DI exceptions naming consumer, index, dependency list, module.
- `references/preview-snapshot.md` — preview boot (scan-only) and deterministic-snapshot identity requirements.
- `references/request-context-registration.md` — pre-seeded per-request REQUEST slot plus durable contextId re-parenting.
- `references/dense-metadata-fastpath.md` — density-gated reuse of captured ctor metadata for hot scoped resolution.
- `references/module-distance-ordering.md` — import-graph depth as THE lifecycle ordering key (globals pinned at MAX).
- `references/shutdown-signals.md` — signal latch + await-init + hook ladder + listener removal + re-raise protocol.
- `references/provider-variants.md` — class/value/factory/existing normalization into one wrapper shape (aliases included).
- `references/module-overrides.md` — pre-registration swap matching by reference with token carryover.
- `references/moduleref-create-introspect.md` — ephemeral-wrapper instantiation of unregistered classes + tree-derived scope introspection.
- `references/validation-pipe-transform-ladder.md` — ValidationPipe's transform/revert ladder: constructor-shell primitive swap, forbidUnknownValues seeding, classToPlain gate.
- `references/validation-strip-proto-keys.md` — prototype-pollution stripper with the seven built-in-type exemptions (shared by both pipes).
- `references/standard-schema-pipe.md` — schema-from-argument-metadata validation over Standard Schema v1 (`~standard.validate`, issues|value result).
- `references/logger-boot-buffer.md` — static WrapBuffer capturing (bound fn, raw args) pre-boot; detach-before-drain flush replay.
- `references/route-path-factory-compose.md` — six-stage path composition: version fan-out → module/ctrl/method cartesian → global prefix → edge normalization.
- `references/route-specificity-sorter.md` — literal<param<wildcard<missing kind ranks, first-difference compare, declaration-index tiebreak.
- `references/route-conflict-detection.md` — four-gate pair overlap classifier + duplicate/shadow taxonomy + sort-aware shadow filtering.
- `references/legacy-route-converter.md` — path-to-regexp v6→v8 wildcard auto-conversion ladder with offset-suffixed mid-path names.
- `references/route-info-path-extractor.md` — middleware-path computation: dual-entry wildcard registration ($ sentinel) and exclusion-aware prefixing.
- `references/deferred-route-registration.md` — resolve-then-install separation via onRouteResolved/deferRegistration + metadata copy at install time.
- `references/host-filter-captures.md` — @Host() compile-once filter filling req.hosts per request from positional/group captures.
- `references/context-utils-args-assembly.md` — max-index+1 argument sizing, dense undefined fill, index-aligned metatype merge.
- `references/repl-context-scope.md` — container-backed REPL global scope: null-proto keys, collision suffixes, prototype-shared aliases, lazy help.
- `references/module-path-app-scope.md` — app-id-suffixed MODULE_PATH lookup with legacy bare-key fallback for multi-app isolation.
- `references/parse-array-pipe.md` — string→split→per-item JSON/coerce/delegate ladder with strict-false stopAtFirstError collection mode.
- `references/parse-pipe-family.md` — ParseInt/Bool/UUID/Enum shared skeleton and their strictness differences (anchored int regex, exact bool duals, variant-pinned UUID regexes, reverse-map-stripped enums).
- `references/param-metadata-exchange.md` — internal RouteParamtypes enum → public Paramtype strings before pipe chains fold sequentially.
- `references/route-params-extraction.md` — the total extraction table from adapter request to handler argument values.
- `references/interceptor-chain-lazy-recursion.md` — lazy index-closure interceptor recursion + transformDeferred closed-subscriber gate.
- `references/guard-sequential-shortcircuit.md` — sequential boolean/Promise/Observable guard ladder with first-false stop.
- `references/http-handler-assembly-order.md` — the eight-step per-request proxy order built once per route.
- `references/handler-metadata-unique-key-cache.md` — controller-id-keyed handler metadata cache (name only as fallback).
- `references/sse-terminal-state-machine.md` — settled/closeRequested/finalize funnel over disconnect, error, completion races.
- `references/sse-wire-encoding.md` — W3C event framing: multiline field splitting, comment-only id suppression, deferred headers.
- `references/exception-filter-selection-ladder.md` — catch-all-as-empty-list first-match selection with reversed wiring.
- `references/request-context-latch-proxy.md` — REQUEST_CONTEXT_ID symbol latch + durable-vs-mutating payload seeding.
- `references/route-registration-layering.md` — scoped-fork → host filter → version filter → deferred install pipeline.
- `references/execution-context-self-extension.md` — one args-triple context, three transport views grafted onto itself.
- `references/enhancer-context-template.md` — global→class→method concat template shared by every enhancer family.
- `references/route-error-funnel-proxy.md` — outermost try/catch turning route throws into filter dispatches (+ error-layer twin).
- `references/boot-wiring-notfound-errorhandlers.md` — throwing not-found handler, framework-error translation, app-suffixed MODULE_PATH.
- `references/contextid-identity-strategy.md` — reference-identity context ids, symbol-latch reuse, strategy re-parenting hook.
- `references/reply-falsy-status-isnil-gate.md` — `!isNil(statusCode)` presence gate in both HTTP adapters' reply(): forwarding 0/NaN instead of dropping them.
- `references/adapter-order-sensitivity-partition.md` — express true / fastify false / default true; one flag gates specificity sorting AND duplicate-rejection policy.
- `references/fastify-constraint-storage-versioning.md` — version matching as find-my-way router constraints (validate/storage/deriveConstraint triad) vs express wrapper filters.
- `references/fastify-middie-pending-queue.md` — pre-init use() parks arg tuples, init() drains FIFO after middie registers.
- `references/express-notfound-prefix-skip.md` — root-mounted 404 middleware skips other apps' prefixes with segment-exact, late-binding matching.
- `references/io-adapter-namespace-gate.md` — create() three-arm ladder over {namespace, server}: when server.of fires and when it must not.
- `references/pattern-route-normalization.md` — sorted-key canonical route strings shared by client and server, depth/key-guard sentinels, unchanged non-pattern passthrough.
- `references/rpc-event-handler-chain.md` — duplicate-pattern registry: message handlers overwrite, event handlers tail-append a linked list composed via forkJoin.
- `references/rpc-send-drain-queue.md` — latch-guarded nextTick drain serializing broker responses with dispose coalescing into the last packet.
- `references/client-proxy-correlation-ladder.md` — cold send / hot emit split, random packet-id routingMap slots, three-arm WritePacket observer ladder.
- `references/redis-reply-refcount-reconnect.md` — refcounted reply channel, unknown-id drop, fail-close flush of pending waiters, three-stage reconnect ladder.
- `references/listener-registration-pipeline.md` — metadata scan → transport filter → static proxy or request-scoped closure with WeakMap-cached rpc exception funnel.
- `references/grpc-route-registry-parallel.md` — exact-string {service,rpc,streaming} registry that bypasses the canonical normalizer on BOTH ends; path-split service fallback; RX→PT streaming ladder.
- `references/grpc-stream-write-backpressure.md` — never-rejecting Observable→Writable machine: drain buffering, deferred error/complete, cancel-resolves-successfully.
- `references/grpc-client-service-factory.md` — proto stub factory over a deliberately-throwing ClientProxy surface; cold per-call observables with cancel latches.
- `references/kafka-header-correlation-server.md` — correlation/reply/terminal flags in headers; resolve-on-first-value replay bridge; pre-value KafkaRetriableException redelivery.
- `references/kafka-client-reply-topic-pinning.md` — `${pattern}.reply` subscription + min-partition pinning from consumer-group assignments; fail-fast unknown reply topics.
- `references/broker-wildcard-matchers.md` — RMQ/MQTT segment-wildcard matchers: exact-first fallback scan, terminal-only #, $share prefix strip, broker-level binding.
- `references/tcp-jsonsocket-framing.md` — len#json framing codec: iterative reassembly loop, StringDecoder codepoint safety, buffer cap fail-fast, fail-close error/FIN.

## Capsule map
- **Module identity & registration** — `opaque-module-tokens.md`: symbol-cached opaque tokens dedupe dynamic modules; `container-registration.md`: token-keyed container ops with global MAX-distance pinning; `module-record.md`: Module collections + three implicit core providers; `module-overrides.md`: reference-matched pre-registration swaps preserving tokens.
- **Instance storage & scopes** — `instance-wrapper.md`: context×inquirer keyed caches with shell clones; `transient-isolation.md`: effective-inquirer id composition; `request-context-registration.md`: seeded REQUEST slot + durable re-parenting; `dense-metadata-fastpath.md`: hole-probing fast path for captured deps; `provider-variants.md`: four provider flavors normalized to one shape.
- **Resolution engine** — `constructor-resolution.md`: barrier-gated concurrent param resolution; `settlement-signal.md`: pending join + cycle detection + rollback; `provider-lookup-ladder.md`: exports-aware import DFS, first match wins; `forwardref-resolution.md`: deferred load + Object.assign merge onto shells; `dependency-tree-introspection.md`: memoized subtree staticity/durability; `barrier-primitive.md`: reusable rendezvous primitive; `error-enrichment.md`: pinpointing DI failure messages.
- **Bootstrap & lifecycle** — `bootstrap-pipeline.md`: strict scan→instantiate→apply phases in one error zone; `metadata-scanning.md`: two-phase scan + APP_* rewiring; `prototype-prepass.md`: shells-before-constructors two-pass loader; `internal-core-module.md`: global internals module registered first; `lifecycle-hooks.md`: distance-descending hook ordering; `module-distance-ordering.md`: TopologyTree depth assignment; `shutdown-signals.md`: once-per-signal teardown protocol.
- **Router & URL machinery** — `route-path-factory-compose.md`: version/module/ctrl/method/prefix composition order; `route-specificity-sorter.md`: stable kind-rank ordering with declaration ties; `route-conflict-detection.md`: pair overlap gates + duplicate/shadow policy + sort-aware filtering; `legacy-route-converter.md`: v6→v8 wildcard conversion ladder; `route-info-path-extractor.md`: middleware wildcard/exclusion path computation; `deferred-route-registration.md`: resolve-then-install with metadata copy; `host-filter-captures.md`: @Host() matching into req.hosts; `module-path-app-scope.md`: app-id-suffixed MODULE_PATH resolution; `route-params-extraction.md`: request→argument extraction table.
- **Validation & pipes** — `validation-pipe-transform-ladder.md`: transform/revert branches + validatorOptions gate; `validation-strip-proto-keys.md`: pollution stripper + built-in exemptions; `standard-schema-pipe.md`: Standard Schema v1 pipe; `parse-array-pipe.md`: split/coerce/delegate ladder + stopAtFirstError; `parse-pipe-family.md`: ParseInt/Bool/UUID/Enum skeleton + strictness matrix; `param-metadata-exchange.md`: enum→string token exchange before sequential folds.
- **Argument assembly & REPL** — `context-utils-args-assembly.md`: max-index sizing + dense fill + metatype merge; `repl-context-scope.md`: container-backed REPL scope/aliases/help.
- **Logging** — `logger-boot-buffer.md`: pre-boot capture buffer with deferred replay.
- **Runtime surfaces** — `instance-links.md`: flattened lookup index for get()/resolve(); `lazy-module-loading.md`: scoped pipeline re-run after boot; `handler-composition.md`: route-handler onion assembly; `moduleref-create-introspect.md`: ad-hoc construction + scope introspection; `preview-snapshot.md`: non-instantiating boot and deterministic identity.
- **Request lifecycle & enhancers (pass 3)** — `enhancer-context-template.md`: global→class→method concat + scoped-global re-resolution template; `interceptor-chain-lazy-recursion.md`: lazy subscribe-time chain with closed-subscriber gate; `guard-sequential-shortcircuit.md`: sequential three-shape guard ladder; `http-handler-assembly-order.md`: guards→status→headers→SSE-signal→interceptors→pipes→response order; `handler-metadata-unique-key-cache.md`: opaque-id-keyed metadata cache; `execution-context-self-extension.md`: one host, grafted transport views; `contextid-identity-strategy.md`: reference-identity ids + latch + strategy hook.
- **Streaming & response plane (pass 3)** — `sse-terminal-state-machine.md`: settled/finalize SSE races incl. mid-await disconnect; `sse-wire-encoding.md`: event-stream framing contract; `route-error-funnel-proxy.md`: try/catch funnel + error-layer translation; `exception-filter-selection-ladder.md`: first-match catch-all selection, reversed wiring; `boot-wiring-notfound-errorhandlers.md`: throwing 404 + app-suffixed module paths.
- **Registration & scoped proxies (pass 3)** — `route-registration-layering.md`: fork→host→version→deferred-install layering; `request-context-latch-proxy.md`: REQUEST_CONTEXT_ID latch + loadPerContext error delegation.
- **Microservices transport kernel (pass 5)** — `pattern-route-normalization.md`: canonical order-independent pattern routes with guard sentinels; `rpc-event-handler-chain.md`: overwrite-vs-tail-append handler registry + forkJoin fan-out; `rpc-send-drain-queue.md`: serialized response drain with dispose coalescing; `client-proxy-correlation-ladder.md`: per-id correlation slots + cold/hot split + observer ladder; `redis-reply-refcount-reconnect.md`: refcounted subscriptions, unknown-id drop, fail-close flush, reconnect ladder; `listener-registration-pipeline.md`: scan→transport-filter→static/request-scoped wiring with rpc error funnel.
- **Host transport adapter plane (pass 4)** — `reply-falsy-status-isnil-gate.md`: presence-not-truthiness status gate shared by both adapters' reply(); `adapter-order-sensitivity-partition.md`: one capability bit → sort+defer vs insert-order, conservative `?? true` default; `fastify-constraint-storage-versioning.md`: router-native constraint versioning (validate/storage/derive triad) vs express wrapper ladder; `fastify-middie-pending-queue.md`: FIFO park-replay of pre-init middleware; `express-notfound-prefix-skip.md`: segment-exact late-binding prefix skip for multi-app 404s; `io-adapter-namespace-gate.md`: Server|Namespace decision ladder with the `namespace &&` gate on server.of.
- **Transport planes II: gRPC / Kafka / wildcards / TCP (pass 6)** — `grpc-route-registry-parallel.md`: exact-string structured registry bypassing normalization at both ends; `grpc-stream-write-backpressure.md`: drain-buffered Observable→Writable with deferred terminals; `grpc-client-service-factory.md`: throwing inherited surface + memoized proto stub factory with cancel ladders; `kafka-header-correlation-server.md`: header envelope + first-value replay bridge + retriable redelivery window; `kafka-client-reply-topic-pinning.md`: reply-topic subscription + min-partition group pinning; `broker-wildcard-matchers.md`: RMQ/MQTT wildcard fallback matching over canonical routes; `tcp-jsonsocket-framing.md`: length-delimited JSON codec with fail-close semantics.

## Extending the foundation
Add one source-confirmed capsule: loader line, map entry, decisive source, invariant, direct-test probe, and `search_graph` retrieval.

## Provenance
nest (MIT), `master@4c38a5ab1` (passes 1-3 at `61b03510`; pass 4 after ff-pull across 44 first-parent upstream commits); Codebase Memory project `nest` (full mode, re-indexed IN PLACE via live-symlink root — no stale twin: 13,265 nodes / 45,266 edges @4c38a5ab1, content-freshness verified by resolving `FastifyAdapter.reply :438-496`; parse_partial only integration/mosquitto.conf + 2 microservices decorator specs — none cited here). Pass 1: injector kernel (28 capsules). Pass 2: router/URL machinery, validation/parse pipes, logger buffer, REPL context (18 capsules). Pass 3: request-lifecycle/enhancer plane + SSE streaming/response plane + registration/scoped proxies (14 capsules; graph retrieval re-verified live rank#1-3 at this pin). Pass 4: host-transport adapter plane mined from the e03cf5c86 falsy-status drift window (6 capsules; all retrieves live-resolved on twin project `nest`). Pass 5: microservices transport kernel (6 capsules at this same pin; graph root/HEAD re-verified live — master@4c38a5ab100f, full mode, generation 2026-08-24T13:53:31Z, 13,265 nodes / 45,266 edges, coverage clean for every cited path; all six seam retrieves resolved rank#1-2 at this pin; repo vitest deps not installed so direct-test execution was BLOCKED — probe expectations quoted verbatim from spec sources). Pass 6: remaining transport planes (7 capsules at this same pin; graph root/HEAD re-verified live — master@4c38a5ab100f, full mode, 13,265 nodes / 45,266 edges, `check_index_coverage` clean (`no_recorded_issue`/`metadata_match`) for all 32 cited source+test paths; per-capsule retrieves resolved rank#1-2 live: writeObservableToGrpc/bufferUntilDrained, ClientGrpcProxy stream/unary methods, combineStreamsAndThrowIfRetriable, matchRmqPattern/matchMqttPattern, JsonSocket + single-caller handleData trace, ClientKafka.createResponseCallback trace; direct-test execution still BLOCKED — probes pinned verbatim from whole-file spec reads incl. server-grpc.spec (1006 ln), client-grpc.spec, server-kafka.spec, client-kafka.spec, server-rmq.spec, server-mqtt.spec, json-socket suite).

## Full view (memory graph)
Revalidate `nest` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt the injector kernel contracts (token identity, wrapper caching, resolution/barrier/settlement machinery, lifecycle ordering, lookup ladders), the router URL/registration contracts (composition order, specificity ranking, conflict policy, deferred install, param extraction), and the validation pipe contracts (transform ladders, pollution stripping, parse-pipe strictness); pass 3 adds the request-lifecycle contracts (enhancer concat template, lazy interceptor recursion, sequential guard short-circuit, handler assembly order, SSE terminal state machine + wire encoding, exception-filter selection with reversed wiring, REQUEST_CONTEXT_ID latch + scoped proxies, error funnel proxies, reference-identity context ids); pass 4 adds the host-transport adapter contracts (falsy-status presence gate, order-sensitivity/duplicate-rejection capability bit, router-constraint versioning triad, FIFO middleware park-replay, segment-exact not-found prefix skip, Server|Namespace ladder); adapt host-specific surfaces (HTTP adapter storage, Reflect-metadata decoration keys, signal handling, RxJS interop) to your runtime; pass 5 adds the microservices transport-kernel contracts (canonical pattern routes, event-chain handler registry, serialized drain queue, id-keyed client correlation, redis reply refcount/reconnect ladder, listener registration pipeline); omit product features (serializer/deserializer envelope-family detail and microservice bootstrap/close lifecycle wiring — learned pass 6, capsules pending, websockets message mapping internals, GraphInspector serialization, sample apps) unless porting those subsystems wholesale. Known latent traps recorded in-capsule: `Object.keys(validatorOptions).length > 1` gate depends on the forbidUnknownValues seed; header selectors are lowercased; stopAtFirstError is strict-false; SSE headers commit on a macrotask so pre-commit errors can still change status; exception-filter lists are reversed ONCE at wiring; context ids compare by object identity not value; reply() must test `!isNil(statusCode)` — truthiness drops 0/NaN and ships errors under stale 200/201 statuses; `versionConstraint` is a property invisible to name_pattern retrieval; fastify `use()` returns this even while queuing or chained boot wiring breaks.
