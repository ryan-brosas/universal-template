<!-- capsule-v2 -->
# Usage combine — summing token/cost ledgers where `0` and `absent` are different facts

**Source:** Veda (`veda-ts`, MIT, `master@f050518c99fa54a5a0af4a04918aaf01d1ed94e1`); Codebase Memory `veda`. **Question:** How do I accumulate per-call usage stats across a multi-member ensemble without inventing fake zeros for fields some backends never report?

## `?? 0 … || undefined` fold over optional ledger fields
**Path/Symbol:** `src/core/llm.ts:combineUsage` (:101–114); consumed by the ensemble plane (`src/core/ensemble.ts`) to preserve accumulated usage across members.
**Signature:** `function combineUsage(usages: (UsageStats | undefined)[]): UsageStats` with `UsageStats = { inputTokens: number; outputTokens: number; cachedTokens?: number; costUsd?: number }`.
**Data Shape:** Required core (input/outputTokens) always sums; optional observability fields (cachedTokens, costUsd) collapse back to `undefined` when no member reported them.

### Decisive source
```ts
export function combineUsage(usages: (UsageStats | undefined)[]): UsageStats {
  return usages.reduce<UsageStats>(
    (acc, u) => {
      if (!u) return acc;
      return {
        inputTokens: acc.inputTokens + u.inputTokens,
        outputTokens: acc.outputTokens + u.outputTokens,
        cachedTokens: (acc.cachedTokens ?? 0) + (u.cachedTokens ?? 0) || undefined,
        costUsd:     (acc.costUsd     ?? 0) + (u.costUsd     ?? 0) || undefined,
      };
    },
    { inputTokens: 0, outputTokens: 0 }
  );
}
```

**Flow:** start from zeroed required core → skip undefined member stats entirely → add required fields unconditionally → for optional fields: treat missing as 0 DURING the addition, then `|| undefined` collapses an all-zero result back to absent.
**Invariant:** `(x ?? 0) + (y ?? 0) || undefined` — the trailing `|| undefined` is load-bearing: it distinguishes "nobody reported cached tokens" from "backends reported 0", which matters for display honesty and downstream metering. A naive `{...acc, ...u}` spread would also silently DROP fields when later members omit them; this fold never loses a reported value.
**Probe:** `tests/core/ensemble-retry.test.ts` pins that accumulated usage survives retries/parallel fan-out through the ensemble path that calls combineUsage.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-ecosystem-veda", query: "combineUsage UsageStats reduce", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the fold expression verbatim — both halves (`?? 0` inside, `|| undefined` outside) are the contract. Adapt field names to your usage schema. Omit nothing.
