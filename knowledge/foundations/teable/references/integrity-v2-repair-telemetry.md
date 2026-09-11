<!-- capsule-v2 -->
# Repair telemetry twin-capture — how do you observe a failing result stream WITHOUT swallowing its exception?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** What is the decorator shape that captures both per-result errors and thrown stream exceptions to Sentry+tracing?

## decorateRepairStream + captureRepairFailure
**Path/Symbol:** `apps/nestjs-backend/src/features/integrity/integrity-v2.service.ts:decorateRepairStream` (:745–782), `:captureRepairFailure` (:791–883); sibling `decorateCheckStream` :729–744 (no telemetry — checks don't repair), `combineRepairStreams` :783–790.
**Signature:** `decorateRepairStream(table, stream, statuses?, telemetry?: {tracer?; scope:'table'|'base'; targetId})`.
**Data Shape:** Two failure kinds: `'result_error'` (stream item with status==='error') and `'stream_exception'` (throw mid-iteration).

### Decisive source
```ts
try {
  for await (const result of stream) {
    const serialized = this.serializeRepairResult(table, result);
    if (serialized.status === 'error' && telemetry) {
      await this.captureRepairFailure(table, result, new Error(result.message), telemetry, 'result_error');
    }
    if (!this.shouldIncludeResult(serialized.status, statusFilter)) continue;
    yield serialized;
  }
} catch (error) {
  if (telemetry) {
    await this.captureRepairFailure(table, undefined, error, telemetry, 'stream_exception');
  }
  throw error;   // re-throw AFTER capture — the controller turns it into an SSE error event
}
```

**Flow:** Wrap any repair generator → serialize (scoped ids `${tableId}:${id}`, deep-mutable details/repair-hint copies so downstream can't mutate frozen internals) → error results captured THEN still filtered/yielded per status filter → exceptions captured then RE-THROWN. Capture fans out to a tracer span (`integrity.*` attributes: scope/target/failure_kind/rule_id/outcome/required, fieldId skipped when `'__system__'`) AND a Sentry scope with feature tag `schema-integrity-repair`; no tracer ⇒ Sentry only.
**Invariant:** Telemetry must never replace the exception path — swallowing converts client-visible failures into silent partial repairs. Check streams deliberately carry NO such decorator because they cannot mutate.
**Probe:** `grep -cF "captureRepairFailure" apps/nestjs-backend/src/features/integrity/integrity-v2.service.ts` → ≥3; direct tests `integrity-v2.service.spec.ts` :628 ('captures result-level repair failures…'), :670 ('captures thrown repair stream exceptions…').

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "decorateRepairStream captureRepairFailure sentry span", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt capture-and-rethrow + dual sink telemetry + scoped-id serialization; adapt attribute names/sinks; omit status filtering if your consumers take everything.
