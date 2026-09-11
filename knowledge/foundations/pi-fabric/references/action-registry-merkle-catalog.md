<!-- capsule-v2 -->
# Merkle capability catalog — how do you expose a deterministic, hash-addressed index of every callable action without leaking unbounded content?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** what is the contract for building the `pi-fabric.capability-catalog` snapshot that discovery/memory tiers consume?

## Connected graph-selected seam
**Path/Symbol:** `src/core/action-registry.ts` — `ActionRegistry.catalog` (:291-366), `descriptorHash` (:220-221), `stableJsonValue` (:210-218).
**Signature:** `catalog(context, { provider?, limit? = 1000 (clamped 1..1000, floored), includeProvider? })` → `{ kind: "pi-fabric.capability-catalog", version: 1, root, providers[], totalActions, indexedActions, complete, reasons }`.
**Data Shape:** tree keys `capability:fabric` → `provider:<name>` → `action:<ref>`; every node carries a `descriptorHash`; action head keeps only `{ key, parentKey, ref, name, description, descriptorHash, risk, namespace? }`.

### Decisive source
```ts
const stableJsonValue = (value: unknown): unknown => {
  if (Array.isArray(value)) return value.map(stableJsonValue);
  if (value === null || typeof value !== "object") return value;
  return Object.fromEntries(
    Object.entries(value as Record<string, unknown>)
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([key, nested]) => [key, stableJsonValue(nested)]),
  );
};

const descriptorHash = (value: unknown): string =>
  createHash("sha256").update(JSON.stringify(stableJsonValue(value))).digest("hex");
```

**Flow:** providers sorted by name → per-provider descriptor lists resolved with refs (`provider.action`) → ALL actions sorted globally by ref and truncated to `limit` retained refs → per-provider heads rebuilt containing ONLY retained actions (so truncation is coherent per subtree) → provider hash = sha256 over its OWN metadata plus its actions' hashes; root hash = sha256 over the array of provider hashes — a real Merkle accumulation where any descriptor change flips exactly its own chain up to the root. `complete: indexedActions === totalActions`, otherwise `reasons: ["action_limit"]`.
**Invariant:** determinism is the contract — localeCompare-sorted keys at EVERY level before hashing means identical capability sets always produce byte-identical roots across hosts/runs (mesh consumers can compare roots to detect drift); hashing covers ref+description+inputSchema+outputSchema+risk+namespace but NEVER live results; the catalog is explicitly "navigation metadata, not historical session evidence".
**Probe:** `tests/action-registry.test.ts:104` ("builds deterministic provider/action heads and searches the complete catalog before ranking").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "catalog capability-catalog descriptorHash stableJsonValue providerHeads root", limit: 5, fields: ["signature", "name", "file"] });
```
