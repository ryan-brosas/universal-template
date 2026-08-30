<!-- capsule-v2 -->
# Module wiring & role registration — how do the computed planes assemble at boot?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** Which modules provide which services, and what do dynamic registrations gate?

## ComputedModule + trigger module twins
**Path/Symbol:** `apps/nestjs-backend/src/features/record/computed/computed.module.ts:ComputedModule` (:1–35); `v2/computed-outbox-trigger/computed-outbox-wakeup-producer.module.ts:register` (:72–93); `computed-outbox-wakeup-consumer.module.ts` (:1–30).
**Signature:** static Nest modules; producer uses `static async register(): Promise<DynamicModule>`.

### Decisive source
```ts
providers: [ DbProvider,
  ComputedDependencyCollectorService,   // closure plane
  ComputedEvaluatorService,             // evaluation plane
  ComputedOrchestratorService,          // transaction orchestration
  RecordComputedUpdateService, LinkCascadeResolver,
  PersistedComputedBackfillService ],
exports: [ComputedOrchestratorService, PersistedComputedBackfillService],   // narrow surface
// producer module: async register() because BullModule.registerQueue returns a promise
const bullQueue = BullModule.registerQueue({ name: COMPUTED_OUTBOX_WAKEUP_QUEUE });
```

**Flow:** record-side pipeline exports ONLY the orchestrator + backfill service (callers cannot reach collector/evaluator directly — internal seams stay swappable). Trigger side splits producer (publisher provider via factory injecting config+queue+metrics, wrapped in createRoleAwareWakeupPublisher) from consumer (admission service + handler + processor registered under V2Module). Consumer module imports V2Module for base-container resolution; producer needs no v2 container.
**Invariant:** Narrow exports = enforced layering; async register() exists ONLY where BullMQ queue tokens must exist before providers instantiate. The publisher SYMBOL token decouples interface from BullMQ implementation so tests substitute fakes.
**Probe:** needle verified at pin (:213 exports line); graph retrieval resolves all three files; consumer/producer split pinned by handler specs (:546/:568 role tests).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "ComputedOutboxWakeupProducerModule", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt narrow-export layering + symbol-token publisher; adapt DI framework equivalents; omit decorator boilerplate details.
