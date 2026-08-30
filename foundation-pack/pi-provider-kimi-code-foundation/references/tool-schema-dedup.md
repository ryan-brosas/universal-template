<!-- capsule-v2 -->
# Tool-schema $defs dedup + fingerprint cache — how do you fit large tool schemas under a per-tool byte limit without paying dedup cost every request?

**Source:** pi-provider-kimi-code MIT `main@794330400343d6f0cd0059635187b233c4d90273`; Codebase Memory `pi-provider-kimi-code`. **Question:** A vendor caps `function.parameters` near 15 KB and agent tool suites exceed it — when do you extract repeated fragments into `$defs`, and how do you memoize across turns safely?

## Tool schema dedup with structural fingerprint cache
**Path/Symbol:** `src/schema-dedup.ts` — thresholds 8-10 (`TOOL_SCHEMA_SIZE_THRESHOLD = 14_000`, `MIN_FRAGMENT_SIZE = 50`, `MAX_DEDUP_PASSES = 5`), `deduplicateSchema` 81-129, `hashValue`/`toolsFingerprint` 165-227, public `optimizeToolSchemas` 229-251. Called from `applyKimiPayloadMutations` step 2 (payload.ts:496-498).
**Signature:** `optimizeToolSchemas(tools: unknown[]): unknown[]`; internal `(schema: JsonRecord): JsonRecord`.
**Data Shape:** per-tool decision on serialized byte size; fragment map of JSON-stringified subnode → list of tree paths; result cache = one (fingerprint, tools) pair.

### Decisive source
```ts
const savings =
  active.length * fragmentSize - (fragmentSize + defsEntryOverhead + active.length * refSize);
if (savings <= 0) continue;
...
if (!progress) break;
}

if (Object.keys(defs).length > 0) {
  result.$defs = defs;
}

if (jsonSize(result) >= originalSize) return schema;
return result;
```
```ts
case "number":
  hash.update(`n:${Object.is(value, -0) ? "-0" : String(value)}`);
  return;
...
if (seen.has(value)) {
  hash.update(`R:${identityId(value as object)}`);
  return;
}
```

**Flow:** skip every tool whose parameters serialize ≤14 KB → collect all ≥50-byte subnodes by exact serialized equality, keep those appearing ≥2 times outside already-replaced subtrees (descendant suppression via path prefix check) → for each candidate in largest-first order compute true savings (N copies vs one $defs entry + N refs) and replace paths with `{"$ref":"#/$defs/dN"}` only if savings > 0 → repeat ≤5 passes while any pass made progress → final guard: if the rewritten schema did not shrink, return the original untouched. Cache: sha256 over a hand-rolled structural walk that distinguishes `-0`, functions/symbols by identity, cycles by `R:<id>`, and non-plain objects by identity — cases where `JSON.stringify` collides or throws; identical fingerprints return the cached optimized array.
**Invariant:** Dedup is never size-increasing (byte-accounted per candidate AND re-verified whole-schema); pre-existing `$defs` keys are merged without collision; the cache must invalidate on ANY content change including equal-length description edits — hence the structural hash instead of stringified length.

**Probe:** `tests/schema-dedup.test.ts:47-251` — line 96 pins every corpus tool under the 15 KB limit after optimization; 122 pins pre-existing `$defs.existing` preserved; 184/209 pin never-larger and never-push-over-limit; 298 pins invalidation when "serialized length is identical but content differs"; 357-428 pin tolerance for non-serializable entries.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-provider-kimi-code", query: "optimizeToolSchemas deduplicateSchema toolsFingerprint", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt threshold-gated, savings-accounted, multi-pass $ref extraction plus the collision-proof structural fingerprint cache; both halves are needed (naive stringify caching breaks on cyclic tool objects). Adapt the 14 KB threshold / 50-byte minimum to your endpoint's real limit. Omit the corpus-normalization tests' fixture machinery; keep a never-grow regression test. No coverage caveat at this pin.
