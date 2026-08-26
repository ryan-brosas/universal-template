<!-- capsule-v2 -->
# Site audit phases — how do you checkpoint PAID calls so retries can't re-buy them, and replay robots.txt exactly?

**Source:** OpenSEO MIT `main@cd6a7820`; Codebase Memory `ext-open-seo`. **Question:** How are discovery/crawl/lighthouse/finalize phases split into steps, and what do the `-v2` / legacy-shape guards protect?

## Phase machine with paid-call checkpoint isolation
**Path/Symbol:** `src/server/workflows/siteAuditWorkflowPhases.ts:runAuditPhases` (:52-104), `runLighthousePhase` (:175-282), `runDiscoveryPhase` (:106-164), `finalizeAudit` (:318-386).
**Signature:** `async function runAuditPhases(step: WorkflowStep, params: AuditPhasesParams): Promise<void>` — phases: discover-urls-v2 → crawl chunks → select-lighthouse-sample → per-URL fetch/persist → multipage-checks → finalize.
**Data Shape:** `LEGACY_LIGHTHOUSE_URL_BATCH_SIZE=10`, `SEED_RPC_BATCH=2000`; step configs from `auditStepConfigs.ts` (DISCOVERY_STEP, LIGHTHOUSE_FETCH_STEP, LIGHTHOUSE_PERSIST_STEP, DB_STEP…); lighthouse batch boundary union `{ schema: "retry-safe-v2" } | { completed; failed }`.

### Decisive source
```ts
// Parsed outside the step from checkpointed text, so replays see the exact
// robots rules the original run used (a live re-fetch could differ and
// desync the frontier from already-persisted crawl batches).
const robots = parseRobotsTxt(origin, discovery.robotsText);
// The paid calls are checkpointed separately from all storage. With Workflow
// retries disabled, a later R2/DB/progress failure cannot replay DataForSEO.
const fetched = await pgStep(step, `lighthouse-fetch-${index + 1}`, LIGHTHOUSE_FETCH_STEP,
  () => Promise.all([fetchLighthouseResult(url, pageId, "mobile", …), fetchLighthouseResult(url, pageId, "desktop", …)]));
const counts = await pgStep(step, `lighthouse-persist-${index + 1}`, LIGHTHOUSE_PERSIST_STEP, /* store only */);
```

**Flow:** discovery returns ONLY `{robotsText, seededCount}` (seeds live in the DO) → robots parsed from the CHECKPOINTED text outside the step → crawl phase streams chunks through the scratchpad → lighthouse sample selected from DB → per URL: one compact paid-fetch checkpoint (mobile+desktop together) then a separate storage/persist checkpoint; a legacy cached boundary shape (`{completed, failed}` under the old name) means that batch's results are already persisted — skip instead of buying again; step-name `-v2` suffixes force replays of pre-refactor instances to re-run rather than resume from incompatible shapes → finalize guards integrity (crawl claimed pages but none persisted ⇒ throw), runs multipage + link checks, completes audit, clears KV progress, destroys scratchpad.
**Invariant:** Paid vendor calls get their OWN checkpoints separate from storage writes — with retries disabled, a later storage failure must not replay the vendor. Anything read by later phases (robots) is parsed from persisted text, never re-fetched live. Old checkpoint shapes are detected and skipped, never misinterpreted.
**Probe:** `src/server/workflows/siteAuditWorkflowPhases.test.ts` (phase sequencing + legacy-boundary skip).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-seo", query: "runLighthousePhase LighthouseBatchBoundary retry-safe-v2 parseRobotsTxt checkpoint", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: paid-call checkpoint isolation, replay-from-checkpoint for external state that must stay consistent, schema-versioned checkpoint names. Adapt batch sizes and phase list to your crawler. Omit Lighthouse entirely if you don't score vitals.
