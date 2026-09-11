<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->

# nest: Dependency-injection container, router & pipe foundation

## Use this for
Use when implementing a DI/IoC container (module graph, provider resolution, scopes), a framework bootstrap/lifecycle pipeline (init/destroy/shutdown hooks), request-scoped injection, lazy module loading, test-oriented module overrides, route-path composition/versioning/specificity ordering, argument validation & coercion pipes, or boot-time log buffering. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./opaque-module-tokens.md` — how module instances dedupe by symbol-cached opaque token instead of class identity.
- `./container-registration.md` — token-keyed addModule/addProvider contract with distance-pinned globals.
- `./module-record.md` — what a Module owns: five collections plus implicit self/ModuleRef/config providers.
- `./instance-wrapper.md` — dual-keyed instance cache (contextId × transient inquirer) with lazy prototype-shell clones.
- `./constructor-resolution.md` — concurrent ctor-param resolution gated by an all-participants Barrier.
- `./settlement-signal.md` — pending/join protocol that makes concurrent loads safe and detects cycles.
- `./provider-lookup-ladder.md` — self → imports visibility ladder with first-export-match-wins.
- `./forwardref-resolution.md` — circular-import survival via thunk unwrap + deferred load + prototype merge.
- `./dependency-tree-introspection.md` — memoized static/durable subtree analysis with ancestor-fan-in invalidation.
- `./transient-isolation.md` — effective-inquirer re-keying so nested transients never share instances.
- `./bootstrap-pipeline.md` — scan-all → instantiate-all → apply-globals inside one ExceptionsZone boundary.
- `./metadata-scanning.md` — decorator-metadata to container records, incl. APP_* UUID-token rewire + deferred apply.
- `./prototype-prepass.md` — two-pass instantiation: shell prototypes for all wrappers before any constructor runs.
- `./internal-core-module.md` — hidden global module exposing REQUEST/INQUIRER/Reflector via container-closure factories.
- `./lazy-module-loading.md` — post-boot modules via scoped re-run of the standard scan+instantiate pipeline.
- `./lifecycle-hooks.md` — distance-descending init order, per-level fan-out, exact reversal for teardown.
- `./instance-links.md` — flattened token→links index powering get()/resolve() with strict/non-strict semantics.
- `./handler-composition.md` — the guards→interceptors→pipes→handler→filter onion built once per route.
- `./barrier-primitive.md` — 55-line rendezvous primitive; zero-count fast path and unconditional error signaling.
- `./error-enrichment.md` — context-carrying DI exceptions naming consumer, index, dependency list, module.
- `./preview-snapshot.md` — preview boot (scan-only) and deterministic-snapshot identity requirements.
- `./request-context-registration.md` — pre-seeded per-request REQUEST slot plus durable contextId re-parenting.
- `./dense-metadata-fastpath.md` — density-gated reuse of captured ctor metadata for hot scoped resolution.
- `./module-distance-ordering.md` — import-graph depth as THE lifecycle ordering key (globals pinned at MAX).
- `./shutdown-signals.md` — signal latch + await-init + hook ladder + listener removal + re-raise protocol.
- `./provider-variants.md` — class/value/factory/existing normalization into one wrapper shape (aliases included).
- `./module-overrides.md` — pre-registration swap matching by reference with token carryover.
- `./moduleref-create-introspect.md` — ephemeral-wrapper instantiation of unregistered classes + tree-derived scope introspection.
- `./validation-pipe-transform-ladder.md` — ValidationPipe's transform/revert ladder: constructor-shell primitive swap, forbidUnknownValues seeding, classToPlain gate.
- `./validation-strip-proto-keys.md` — prototype-pollution stripper with the seven built-in-type exemptions (shared by both pipes).
- `./standard-schema-pipe.md` — schema-from-argument-metadata validation over Standard Schema v1 (`~standard.validate`, issues|value result).
- `./logger-boot-buffer.md` — static WrapBuffer capturing (bound fn, raw args) pre-boot; detach-before-drain flush replay.
- `./route-path-factory-compose.md` — six-stage path composition: version fan-out → module/ctrl/method cartesian → global prefix → edge normalization.
- `./route-specificity-sorter.md` — literal<param<wildcard<missing kind ranks, first-difference compare, declaration-index tiebreak.
- `./route-conflict-detection.md` — four-gate pair overlap classifier + duplicate/shadow taxonomy + sort-aware shadow filtering.
- `./legacy-route-converter.md` — path-to-regexp v6→v8 wildcard auto-conversion ladder with offset-suffixed mid-path names.
- `./route-info-path-extractor.md` — middleware-path computation: dual-entry wildcard registration ($ sentinel) and exclusion-aware prefixing.
- `./deferred-route-registration.md` — resolve-then-install separation via onRouteResolved/deferRegistration + metadata copy at install time.
- `./host-filter-captures.md` — @Host() compile-once filter filling req.hosts per request from positional/group captures.
- `./context-utils-args-assembly.md` — max-index+1 argument sizing, dense undefined fill, index-aligned metatype merge.
- `./repl-context-scope.md` — container-backed REPL global scope: null-proto keys, collision suffixes, prototype-shared aliases, lazy help.
- `./module-path-app-scope.md` — app-id-suffixed MODULE_PATH lookup with legacy bare-key fallback for multi-app isolation.
- `./parse-array-pipe.md` — string→split→per-item JSON/coerce/delegate ladder with strict-false stopAtFirstError collection mode.
- `./parse-pipe-family.md` — ParseInt/Bool/UUID/Enum shared skeleton and their strictness differences (anchored int regex, exact bool duals, variant-pinned UUID regexes, reverse-map-stripped enums).
- `./param-metadata-exchange.md` — internal RouteParamtypes enum → public Paramtype strings before pipe chains fold sequentially.
- `./route-params-extraction.md` — the total extraction table from adapter request to handler argument values.
- `./interceptor-chain-lazy-recursion.md` — lazy index-closure interceptor recursion + transformDeferred closed-subscriber gate.
- `./guard-sequential-shortcircuit.md` — sequential boolean/Promise/Observable guard ladder with first-false stop.
- `./http-handler-assembly-order.md` — the eight-step per-request proxy order built once per route.
- `./handler-metadata-unique-key-cache.md` — controller-id-keyed handler metadata cache (name only as fallback).
- `./sse-terminal-state-machine.md` — settled/closeRequested/finalize funnel over disconnect, error, completion races.
- `./sse-wire-encoding.md` — W3C event framing: multiline field splitting, comment-only id suppression, deferred headers.
- `./exception-filter-selection-ladder.md` — catch-all-as-empty-list first-match selection with reversed wiring.
- `./request-context-latch-proxy.md` — REQUEST_CONTEXT_ID symbol latch + durable-vs-mutating payload seeding.
- `./route-registration-layering.md` — scoped-fork → host filter → version filter → deferred install pipeline.
- `./execution-context-self-extension.md` — one args-triple context, three transport views grafted onto itself.
- `./enhancer-context-template.md` — global→class→method concat template shared by every enhancer family.
- `./route-error-funnel-proxy.md` — outermost try/catch turning route throws into filter dispatches (+ error-layer twin).
- `./boot-wiring-notfound-errorhandlers.md` — throwing not-found handler, framework-error translation, app-suffixed MODULE_PATH.
- `./contextid-identity-strategy.md` — reference-identity context ids, symbol-latch reuse, strategy re-parenting hook.
- `./reply-falsy-status-isnil-gate.md` — `!isNil(statusCode)` presence gate in both HTTP adapters' reply(): forwarding 0/NaN instead of dropping them.
- `./adapter-order-sensitivity-partition.md` — express true / fastify false / default true; one flag gates specificity sorting AND duplicate-rejection policy.
- `./fastify-constraint-storage-versioning.md` — version matching as find-my-way router constraints (validate/storage/deriveConstraint triad) vs express wrapper filters.
- `./fastify-middie-pending-queue.md` — pre-init use() parks arg tuples, init() drains FIFO after middie registers.
- `./express-notfound-prefix-skip.md` — root-mounted 404 middleware skips other apps' prefixes with segment-exact, late-binding matching.
- `./io-adapter-namespace-gate.md` — create() three-arm ladder over {namespace, server}: when server.of fires and when it must not.
- `./pattern-route-normalization.md` — sorted-key canonical route strings shared by client and server, depth/key-guard sentinels, unchanged non-pattern passthrough.
- `./rpc-event-handler-chain.md` — duplicate-pattern registry: message handlers overwrite, event handlers tail-append a linked list composed via forkJoin.
- `./rpc-send-drain-queue.md` — latch-guarded nextTick drain serializing broker responses with dispose coalescing into the last packet.
- `./client-proxy-correlation-ladder.md` — cold send / hot emit split, random packet-id routingMap slots, three-arm WritePacket observer ladder.
- `./redis-reply-refcount-reconnect.md` — refcounted reply channel, unknown-id drop, fail-close flush of pending waiters, three-stage reconnect ladder.
- `./listener-registration-pipeline.md` — metadata scan → transport filter → static proxy or request-scoped closure with WeakMap-cached rpc exception funnel.
- `./grpc-route-registry-parallel.md` — exact-string {service,rpc,streaming} registry that bypasses the canonical normalizer on BOTH ends; path-split service fallback; RX→PT streaming ladder.
- `./grpc-stream-write-backpressure.md` — never-rejecting Observable→Writable machine: drain buffering, deferred error/complete, cancel-resolves-successfully.
- `./grpc-client-service-factory.md` — proto stub factory over a deliberately-throwing ClientProxy surface; cold per-call observables with cancel latches.
- `./kafka-header-correlation-server.md` — correlation/reply/terminal flags in headers; resolve-on-first-value replay bridge; pre-value KafkaRetriableException redelivery.
- `./kafka-client-reply-topic-pinning.md` — `${pattern}.reply` subscription + min-partition pinning from consumer-group assignments; fail-fast unknown reply topics.
- `./broker-wildcard-matchers.md` — RMQ/MQTT segment-wildcard matchers: exact-first fallback scan, terminal-only #, $share prefix strip, broker-level binding.
- `./tcp-jsonsocket-framing.md` — len#json framing codec: iterative reassembly loop, StringDecoder codepoint safety, buffer cap fail-fast, fail-close error/FIN.
- `./incoming-request-deserializer-channel-fallback.md` — how do you accept BOTH enveloped internal packets and raw external payloads with one deserializer?
- `./incoming-response-deserializer-normalization.md` — what should a client do when a reply is a bare foreign value with no correlation envelope?
- `./kafka-request-serializer-shape-ladder.md` — when does a payload become JSON, toString(), or pass through untouched?
- `./kafka-response-deserializer-header-triladder.md` — how do correlation id, error, and stream termination ride alongside the payload?
- `./microservice-close-lifecycle.md` — in what order do transport, clients, hooks, and signals tear down, and what stops double-close?
- `./microservice-listen-lazy-boot.md` — what starts when, and what does preview mode deliberately skip?
- `./record-serializer-wrappers.md` — how do per-message publish options travel when the payload channel can only carry bytes?
- `./nats-inbox-correlation-plane.md` — per-message reply token on the server, per-request inbox subscribed before publish on the client, empty-body terminal error, queue-group work sharing.
- `./rmq-client-replyto-queue-plane.md` — one shared amq.rabbitmq.reply-to consumer fanning out by correlationId over an unlimited-listener emitter; register-listener-before-send; bounded multi-URL failover.
- `./mqtt-client-reply-topic-refcount.md` — `${pattern}/reply` convention with publish-inside-subscribe-callback ordering, refcounted subscriptions vs per-id waiters, options lifted out of the payload.
- `./rpc-decorator-metadata-contract.md` — four-key method metadata (patterns array / handler-kind gate / transport pin / merged extras), overload disambiguation ladder, gRPC decorator family + drainBuffer wrapper.
- `./rpc-context-creator-args-ladder.md` — PAYLOAD/CONTEXT/GRPC_CALL position table over a null-sized args array, parallel pipe fill, guard-denial as RpcException, pre-request hook chain.

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
- **Serializer/deserializer envelopes & microservice lifecycle** — `incoming-request-deserializer-channel-fallback.md`: falsy⇒external, has-pattern-or-data⇒internal, else map channel→pattern; `incoming-response-deserializer-normalization.md`: mirror-image ladder, foreign values are terminal by definition; `kafka-request-serializer-shape-ladder.md`: wrap non-Kafka shapes, encode value/key, default headers {}; `kafka-response-deserializer-header-triladder.md`: err header > disposed header > bare value, keyed by CORRELATION_ID; `microservice-close-lifecycle.md`: transport first, latch second, module closes clients in parallel; `microservice-listen-lazy-boot.md`: listen() boots-if-needed then wraps the server callback, preview gates wiring; `record-serializer-wrappers.md`: unpack INTO the packet, each transport lifts what ITS client can consume.
- **Transport planes III: NATS / RMQ / MQTT clients + RPC declaration plane (pass 8)** — `nats-inbox-correlation-plane.md`: reply token vs inbox-per-request, empty-body⇒terminal, queue groups; `rmq-client-replyto-queue-plane.md`: shared reply-to consumer + correlationId emitter, listener-before-send, URL-bounded failover; `mqtt-client-reply-topic-refcount.md`: subscribe-callback publish ordering + refcount split; `rpc-decorator-metadata-contract.md`: four-key decorator contract + gRPC family derivation; `rpc-context-creator-args-ladder.md`: position-table argument assembly over the shared enhancer consumers.

## Extending the foundation
Add one source-confirmed capsule: loader line, map entry, decisive source, invariant, direct-test probe, and `search_graph` retrieval.

## Provenance
nest (MIT), `master@4c38a5ab1` (passes 1-3 at `61b03510`; pass 4 after ff-pull across 44 first-parent upstream commits); Codebase Memory project `nest` (full mode, re-indexed IN PLACE via live-symlink root — no stale twin: 13,265 nodes / 45,266 edges @4c38a5ab1, content-freshness verified by resolving `FastifyAdapter.reply :438-496`; parse_partial only integration/mosquitto.conf + 2 microservices decorator specs — none cited here). Pass 1: injector kernel (28 capsules). Pass 2: router/URL machinery, validation/parse pipes, logger buffer, REPL context (18 capsules). Pass 3: request-lifecycle/enhancer plane + SSE streaming/response plane + registration/scoped proxies (14 capsules; graph retrieval re-verified live rank#1-3 at this pin). Pass 4: host-transport adapter plane mined from the e03cf5c86 falsy-status drift window (6 capsules; all retrieves live-resolved on twin project `nest`). Pass 5: microservices transport kernel (6 capsules at this same pin; graph root/HEAD re-verified live — master@4c38a5ab100f, full mode, generation 2026-08-24T13:53:31Z, 13,265 nodes / 45,266 edges, coverage clean for every cited path; all six seam retrieves resolved rank#1-2 at this pin; repo vitest deps not installed so direct-test execution was BLOCKED — probe expectations quoted verbatim from spec sources). Pass 6: remaining transport planes (7 capsules at this same pin; graph root/HEAD re-verified live — master@4c38a5ab100f, full mode, 13,265 nodes / 45,266 edges, `check_index_coverage` clean (`no_recorded_issue`/`metadata_match`) for all 32 cited source+test paths; per-capsule retrieves resolved rank#1-2 live: writeObservableToGrpc/bufferUntilDrained, ClientGrpcProxy stream/unary methods, combineStreamsAndThrowIfRetriable, matchRmqPattern/matchMqttPattern, JsonSocket + single-caller handleData trace, ClientKafka.createResponseCallback trace; direct-test execution still BLOCKED — probes pinned verbatim from whole-file spec reads incl. server-grpc.spec (1006 ln), client-grpc.spec, server-kafka.spec, client-kafka.spec, server-rmq.spec, server-mqtt.spec, json-socket suite). Pass 7: serializer/deserializer envelope family + microservice bootstrap/close lifecycle (7 capsules at this same pin; whole-source reads of the codec family + nest-microservice.ts/microservices-module.ts; direct-test execution still BLOCKED — probes pinned verbatim from spec sources). Pass 8: NATS/RMQ/MQTT client planes + RPC declaration/context plane (5 capsules at this same pin; graph MCP not connected this session — direct source+test read fallback per AGENTS.md, Retrieve blocks are expected-rank statements; whole-source reads of server-nats/client-nats/client-rmq/client-mqtt/decorators/rpc-context-creator + nine spec files; direct-test execution still BLOCKED — probes pinned verbatim from spec sources).

## Full view (memory graph)
Revalidate `nest` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt the injector kernel contracts (token identity, wrapper caching, resolution/barrier/settlement machinery, lifecycle ordering, lookup ladders), the router URL/registration contracts (composition order, specificity ranking, conflict policy, deferred install, param extraction), and the validation pipe contracts (transform ladders, pollution stripping, parse-pipe strictness); pass 3 adds the request-lifecycle contracts (enhancer concat template, lazy interceptor recursion, sequential guard short-circuit, handler assembly order, SSE terminal state machine + wire encoding, exception-filter selection with reversed wiring, REQUEST_CONTEXT_ID latch + scoped proxies, error funnel proxies, reference-identity context ids); pass 4 adds the host-transport adapter contracts (falsy-status presence gate, order-sensitivity/duplicate-rejection capability bit, router-constraint versioning triad, FIFO middleware park-replay, segment-exact not-found prefix skip, Server|Namespace ladder); adapt host-specific surfaces (HTTP adapter storage, Reflect-metadata decoration keys, signal handling, RxJS interop) to your runtime; pass 5 adds the microservices transport-kernel contracts (canonical pattern routes, event-chain handler registry, serialized drain queue, id-keyed client correlation, redis reply refcount/reconnect ladder, listener registration pipeline); pass 7 adds the envelope-codec contracts (channel-fallback request deserialization, terminal-by-definition foreign responses, Kafka shape ladder + header tri-ladder, record-wrapper unpacking, transport-first close ordering with module-parallel client teardown, lazy listen boot with preview gates); pass 8 adds the remaining transport-client contracts (NATS inbox-before-publish + empty-body terminal, RMQ shared reply-to correlationId fan-out, MQTT subscribe-callback publish ordering + refcount split) and the RPC declaration plane (four-key decorator metadata contract, gRPC decorator family derivation, position-table argument assembly); omit product features (websockets message mapping internals, GraphInspector serialization, sample apps) unless porting those subsystems wholesale. Known latent traps recorded in-capsule: `Object.keys(validatorOptions).length > 1` gate depends on the forbidUnknownValues seed; header selectors are lowercased; stopAtFirstError is strict-false; SSE headers commit on a macrotask so pre-commit errors can still change status; exception-filter lists are reversed ONCE at wiring; context ids compare by object identity not value; reply() must test `!isNil(statusCode)` — truthiness drops 0/NaN and ships errors under stale 200/201 statuses; `versionConstraint` is a property invisible to name_pattern retrieval; fastify `use()` returns this even while queuing or chained boot wiring breaks.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`adapter-order-sensitivity-partition.md`](./adapter-order-sensitivity-partition.md)
- [`barrier-primitive.md`](./barrier-primitive.md)
- [`boot-wiring-notfound-errorhandlers.md`](./boot-wiring-notfound-errorhandlers.md)
- [`bootstrap-pipeline.md`](./bootstrap-pipeline.md)
- [`broker-wildcard-matchers.md`](./broker-wildcard-matchers.md)
- [`client-proxy-correlation-ladder.md`](./client-proxy-correlation-ladder.md)
- [`constructor-resolution.md`](./constructor-resolution.md)
- [`container-registration.md`](./container-registration.md)
- [`context-utils-args-assembly.md`](./context-utils-args-assembly.md)
- [`contextid-identity-strategy.md`](./contextid-identity-strategy.md)
- [`deferred-route-registration.md`](./deferred-route-registration.md)
- [`dense-metadata-fastpath.md`](./dense-metadata-fastpath.md)
- [`dependency-tree-introspection.md`](./dependency-tree-introspection.md)
- [`enhancer-context-template.md`](./enhancer-context-template.md)
- [`error-enrichment.md`](./error-enrichment.md)
- [`exception-filter-selection-ladder.md`](./exception-filter-selection-ladder.md)
- [`execution-context-self-extension.md`](./execution-context-self-extension.md)
- [`express-notfound-prefix-skip.md`](./express-notfound-prefix-skip.md)
- [`fastify-constraint-storage-versioning.md`](./fastify-constraint-storage-versioning.md)
- [`fastify-middie-pending-queue.md`](./fastify-middie-pending-queue.md)
- [`forwardref-resolution.md`](./forwardref-resolution.md)
- [`grpc-client-service-factory.md`](./grpc-client-service-factory.md)
- [`grpc-route-registry-parallel.md`](./grpc-route-registry-parallel.md)
- [`grpc-stream-write-backpressure.md`](./grpc-stream-write-backpressure.md)
- [`guard-sequential-shortcircuit.md`](./guard-sequential-shortcircuit.md)
- [`handler-composition.md`](./handler-composition.md)
- [`handler-metadata-unique-key-cache.md`](./handler-metadata-unique-key-cache.md)
- [`host-filter-captures.md`](./host-filter-captures.md)
- [`http-handler-assembly-order.md`](./http-handler-assembly-order.md)
- [`incoming-request-deserializer-channel-fallback.md`](./incoming-request-deserializer-channel-fallback.md)
- [`incoming-response-deserializer-normalization.md`](./incoming-response-deserializer-normalization.md)
- [`instance-links.md`](./instance-links.md)
- [`instance-wrapper.md`](./instance-wrapper.md)
- [`interceptor-chain-lazy-recursion.md`](./interceptor-chain-lazy-recursion.md)
- [`internal-core-module.md`](./internal-core-module.md)
- [`io-adapter-namespace-gate.md`](./io-adapter-namespace-gate.md)
- [`kafka-client-reply-topic-pinning.md`](./kafka-client-reply-topic-pinning.md)
- [`kafka-header-correlation-server.md`](./kafka-header-correlation-server.md)
- [`kafka-request-serializer-shape-ladder.md`](./kafka-request-serializer-shape-ladder.md)
- [`kafka-response-deserializer-header-triladder.md`](./kafka-response-deserializer-header-triladder.md)
- [`lazy-module-loading.md`](./lazy-module-loading.md)
- [`legacy-route-converter.md`](./legacy-route-converter.md)
- [`lifecycle-hooks.md`](./lifecycle-hooks.md)
- [`listener-registration-pipeline.md`](./listener-registration-pipeline.md)
- [`logger-boot-buffer.md`](./logger-boot-buffer.md)
- [`metadata-scanning.md`](./metadata-scanning.md)
- [`microservice-close-lifecycle.md`](./microservice-close-lifecycle.md)
- [`microservice-listen-lazy-boot.md`](./microservice-listen-lazy-boot.md)
- [`module-distance-ordering.md`](./module-distance-ordering.md)
- [`module-overrides.md`](./module-overrides.md)
- [`module-path-app-scope.md`](./module-path-app-scope.md)
- [`module-record.md`](./module-record.md)
- [`moduleref-create-introspect.md`](./moduleref-create-introspect.md)
- [`mqtt-client-reply-topic-refcount.md`](./mqtt-client-reply-topic-refcount.md)
- [`nats-inbox-correlation-plane.md`](./nats-inbox-correlation-plane.md)
- [`opaque-module-tokens.md`](./opaque-module-tokens.md)
- [`param-metadata-exchange.md`](./param-metadata-exchange.md)
- [`parse-array-pipe.md`](./parse-array-pipe.md)
- [`parse-pipe-family.md`](./parse-pipe-family.md)
- [`pattern-route-normalization.md`](./pattern-route-normalization.md)
- [`preview-snapshot.md`](./preview-snapshot.md)
- [`prototype-prepass.md`](./prototype-prepass.md)
- [`provider-lookup-ladder.md`](./provider-lookup-ladder.md)
- [`provider-variants.md`](./provider-variants.md)
- [`record-serializer-wrappers.md`](./record-serializer-wrappers.md)
- [`redis-reply-refcount-reconnect.md`](./redis-reply-refcount-reconnect.md)
- [`repl-context-scope.md`](./repl-context-scope.md)
- [`reply-falsy-status-isnil-gate.md`](./reply-falsy-status-isnil-gate.md)
- [`request-context-latch-proxy.md`](./request-context-latch-proxy.md)
- [`request-context-registration.md`](./request-context-registration.md)
- [`rmq-client-replyto-queue-plane.md`](./rmq-client-replyto-queue-plane.md)
- [`route-conflict-detection.md`](./route-conflict-detection.md)
- [`route-error-funnel-proxy.md`](./route-error-funnel-proxy.md)
- [`route-info-path-extractor.md`](./route-info-path-extractor.md)
- [`route-params-extraction.md`](./route-params-extraction.md)
- [`route-path-factory-compose.md`](./route-path-factory-compose.md)
- [`route-registration-layering.md`](./route-registration-layering.md)
- [`route-specificity-sorter.md`](./route-specificity-sorter.md)
- [`rpc-context-creator-args-ladder.md`](./rpc-context-creator-args-ladder.md)
- [`rpc-decorator-metadata-contract.md`](./rpc-decorator-metadata-contract.md)
- [`rpc-event-handler-chain.md`](./rpc-event-handler-chain.md)
- [`rpc-send-drain-queue.md`](./rpc-send-drain-queue.md)
- [`settlement-signal.md`](./settlement-signal.md)
- [`shutdown-signals.md`](./shutdown-signals.md)
- [`sse-terminal-state-machine.md`](./sse-terminal-state-machine.md)
- [`sse-wire-encoding.md`](./sse-wire-encoding.md)
- [`standard-schema-pipe.md`](./standard-schema-pipe.md)
- [`tcp-jsonsocket-framing.md`](./tcp-jsonsocket-framing.md)
- [`transient-isolation.md`](./transient-isolation.md)
- [`validation-pipe-transform-ladder.md`](./validation-pipe-transform-ladder.md)
- [`validation-strip-proto-keys.md`](./validation-strip-proto-keys.md)
