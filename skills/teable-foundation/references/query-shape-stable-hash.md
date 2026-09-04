<!-- capsule-v2 -->
# Execution-shape-blind shape hashing — how do you key recommendations on query structure when every observation carries different timings?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How is a stable identity derived for "the same query" across windows so observations aggregate and recommendations dedupe?

## Hash everything EXCEPT the execution shape
**Path/Symbol:** `packages/v2/table-query-ops/src/domain.ts`: `TableQueryShape.shapeHash` (:507-510), `stableHash` (:1357-1364), `sortDeep` (:1366-1378); consumer `TableQueryObservationWindow.create` (:573-601) stamps `shapeHash: raw.shapeHash ?? raw.shape.shapeHash()`.
**Signature:** `shapeHash(): string`; `stableHash(input: unknown): string` → 8-hex-char string.
**Data Shape:** hash input = full snapshot minus `executionShape`. stableHash = JSON.stringify(sortDeep(x)) folded with `(hash*31 + charCode) >>> 0`, hex-padded to 8. sortDeep sorts object keys with `localeCompare`, recurses arrays/objects, leaves primitives.

### Decisive source
```ts
shapeHash(): string {
  const { executionShape: _executionShape, ...structure } = this.value;
  return stableHash(structure);
}
```

**Flow:** shape created (literals vetoed, fields sorted) → window.create computes/stamps shapeHash once → repositories upsert observations additively keyed by the hash; recommendation lookup uses `(tableId, shapeHash, policyVersion)` so one slow execution and forty fast ones with identical structure land on the same recommendation.
**Invariant:** Two queries differing ONLY in duration/timeouts/result counts MUST share a hash — that's the point (structure identifies, execution measures). The corollary trap for porters: never add an execution-derived field into the hashed structure, and keep key-sorting deterministic (JS object key order would otherwise make hashes unstable across builds).
**Probe:** `domain.spec.ts:100` "normalizes selected search fields and hashes query structure without execution timings".
**Coverage caveat:** none — direct spec pins both normalization and timing-blindness.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "TableQueryShape shapeHash stableHash sortDeep", limit: 6, fields: ["signature","name","file"] });
```

## Verdict
Adopt the destructure-out-the-volatile-field hashing pattern and the sorted-keys canonical form; adapt the 31-base fold if you need cryptographic strength elsewhere (this is deliberately NOT crypto — it buckets, not authenticates); omit the specific field set. Note `stableHash` is also reused by sqlDiagnostics fingerprints — same primitive, two consumers.
