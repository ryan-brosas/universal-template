<!-- capsule-v2 -->
# Branch summary versioned envelope — how do you accept a new summary shape without breaking stored old ones?

**Source:** pi-fabric (MIT), `feat/veda-runner@4874ac3a`; Codebase Memory `pi-fabric`. **Question:** How do persisted compaction summaries evolve from v1 facts to v2 run-facts while every stored envelope stays readable?

## Branch summary versioned envelope
**Path/Symbol:** `src/compaction/branch-details.ts:readFabricBranchSummaryDetails/V1/V2` (:240–269), validators `isFactV1/isFactV2/validEnvelope` (:152–238).
**Signature:** `readFabricBranchSummaryDetails(value: unknown): FabricBranchSummaryDetails | undefined` = `readV2(value) ?? readV1(value)`.
**Data Shape:** Envelope `{kind: "pi-fabric.branch-summary", version: 1|2, source{firstEntryId,lastEntryId,entryCount,oldLeafId?}, facts[], omittedFacts, sections[], request{text,sourceBytes,truncated}}`; fact address invariant `${entryId}/${subordinal}`; v2 adds `{kind:"fabricRun", name, description?, outcome}` with `subordinal` REQUIRED to start `"call:"`.

### Decisive source
```ts
const validBase = (fact: Record<string, unknown>): boolean =>
  typeof fact.entryId === "string"
  && typeof fact.subordinal === "string"
  && typeof fact.address === "string"
  && fact.address === `${fact.entryId}/${fact.subordinal}`;   // address is DERIVED, never free-form
```

**Flow:** any unknown blob → try strict v2 (fabricRun facts allowed) → fall back to strict v1 → else `undefined`. Every validator is hand-rolled allowlist style (`hasOnlyKeys` — no extra keys tolerated), so malformed or over-keyed payloads fail loud-quietly (return undefined, never throw to caller).
**Invariant:** Versioned readers are STRICT PER VERSION — a v2 envelope must NOT be accepted by the v1 reader (v2 run facts rejected as v1), yet BOTH stay readable forever from the same union reader; global budgets enforced at validation time: ≤256 facts, ≤64 sections, whole envelope ≤128 KiB serialized bytes; nested JSON inside details is bounded during validation itself (≤4096 nodes, ≤256 per collection, depth ≤16, cycle-rejecting via an ancestors Set); `Buffer.byteLength` byte caps on run name (256B) and description (1024B) — not char counts.
**Probe:** `tests/compaction-trace-branch.test.ts` ("keeps strict v1 branch envelopes readable without accepting v2 run facts as v1"); grep -c 'MAX_DETAILS_JSON_NODES = 4096' src/compaction/branch-details.ts → 1.
**Anchor:** repo root.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "readFabricBranchSummaryDetails validEnvelope facts envelope", limit: 10 });
// validEnvelope Function src/compaction/branch-details.ts 209-238
```

## Verdict
Adopt the strict-per-version + union-reader pattern for any persisted artifact that must outlive schema changes; adapt budget constants to your storage; omit the fabricRun fact family unless you port declared-intent tracing.
