<!-- capsule-v2 -->
# Versioned wakeup wire contract — what does a queue payload carry so any generation of consumer can validate it?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** What is the on-the-wire shape of an outbox wake-up and its evolution rule?

## computedOutboxWakeupWireSchema
**Path/Symbol:** `apps/nestjs-backend/src/features/v2/computed-outbox-trigger/computed-outbox-wakeup.wire.ts:computedOutboxWakeupWireSchema` (:1–18).
**Signature:** `z.object({schemaVersion: z.literal(1), wakeupId: min(1), taskId: min(1), baseId: min(1), availableAt: iso.datetime(), emittedAt: iso.datetime(), cause: enum(['created','merged','retry','replay'])})`.

### Decisive source
```ts
export const computedOutboxWakeupWireSchema = z.object({
  schemaVersion: z.literal(1),
  ...
  cause: z.enum(['created', 'merged', 'retry', 'replay']),
});
export type ComputedOutboxWakeupWire = z.infer<typeof computedOutboxWakeupWireSchema>;
```

**Flow:** every publish serializes through this shape; every consume re-validates (processor safeParse → UnrecoverableError on mismatch); monitor re-validates retained job payloads before display. `schemaVersion: literal(1)` means version-2 consumers reject-and-park v1 payloads rather than guess; cause taxonomy distinguishes first-emission (created/merged) from recovery paths (retry/replay) for metrics and tests.
**Invariant:** The payload is a LOCATOR (task+base ids + timing + cause), never business data — recomputation state lives in durable DB rows, so any replay reconstructs everything from storage. ISO datetime strings, not timestamps.
**Probe:** `bullmq-computed-outbox-wakeup.processor.spec.ts:18–26` (valid envelope fixture); invalid-shape rejection pinned at :33–45.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "computedOutboxWakeupWireSchema", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt locator-only payloads + literal-version gate + cause taxonomy; adapt Zod to your validator; omit nothing — this file is fully portable.
