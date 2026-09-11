<!-- capsule-v2 -->
# Hypercredit number formatting ladders — why does spend keep 4 decimals at 0.002 hc while balance compacts at 10k?

**Source:** pi-hypercharm-provider MIT `main@4520704` (drift re-entry pass 3, was `0bdfab4`); Codebase Memory project `pi-hypercharm-provider` (node `pi-hypercharm-provider.status.trimZeros`, `status.ts:114-116`). **Question:** Three magnitudes (session spend, account balance, rate-limit counts) share one footer — what precision/compaction contract does each follow so a porter doesn't flatten them into one formatter?

## trimZeros core + three asymmetric ladders
**Path/Symbol:** `trimZeros` `status.ts:114-116`; `formatBalHc` :119-126; `formatSpendHc` :128-135; `formatRateCompact` :137-144; line builders `buildSessionLine` :146-149 + `accountHasData` :151-153; optimistic-spend sibling `applyOptimisticSpend` :106-110 sits between the config and formatting planes. DIRECT TESTS: `tests/status.smoke.ts:27-39` pins all three ladders exactly.
**Signature:** all `(n: number): string`, pure and dependency-free.
**Data Shape:** string out; non-finite input renders `"?"` (balance/rate); spend renders `"0"` for ≤0 and `"~0"` below 0.001.

### Decisive source
```ts
function trimZeros(text: string): string {
	return text.includes(".") ? text.replace(/0+$/, "").replace(/\.$/, "") : text;
}
// balance: compact EARLY (≥10k), two tiers
if (abs >= 1_000_000) return `${trimZeros((n / 1_000_000).toFixed(2))}M`;
if (abs >= 10_000)    return `${trimZeros((n / 1_000).toFixed(1))}k`;
return Number.isInteger(n) ? n.toLocaleString("en-US") : trimZeros(n.toFixed(2));
// spend: never compacts; precision LADDER instead
if (n <= 0) return "0";
if (n < 0.001) return "~0";
if (n < 0.01) return trimZeros(n.toFixed(4));
if (n < 1000) return trimZeros(n.toFixed(2));
return Math.round(n).toLocaleString("en-US");
```

**Flow:** session line renders `⚡ <formatSpendHc> hc · <n> req`; account tier atoms join with `" · "`; rate counts render exact under 1000 (`String(Math.max(0, Math.round(n)))`).
**Invariant:** the thresholds are DELIBERATELY asymmetric per semantic: balance compacts at ≥10k because it's a stock figure read at a glance; rate counts stay exact until ≥1000 then use one decimal k; spend NEVER compacts — it widens precision DOWN instead (<0.01 gets four decimals, sub-0.001 becomes the honest approximation marker `"~0"`). `trimZeros` only strips when a "." is present, strips zeros BEFORE the dot, and never mangles an integer string. Smoke-pinned values: `formatBalHc(12345)="12.3k"`, `(1_250_000)="1.25M"`, `(250.5)="250.5"`; `formatSpendHc(0.0004)="~0"`, `(0.0021)="0.0021"`; `formatRateCompact(9996)="10k"`. `accountHasData` treats `authDaysLeft` as NOT data-sufficient on its own (balance/team/rate gate visibility).
**Probe:** `bash -c 'cd $REFERENCE_ROOT/pi-hypercharm-provider && grep -cF "replace(/0+$/" status.ts'` → 1; `grep -cE "1_000_000|10_000" status.ts` → 2; `grep -c "~0" status.ts` → 1; `grep -c "toFixed(4)" status.ts` → 1. Direct runner: `node tests/status.smoke.ts` → "status.smoke: all assertions passed" (Node v26.7.0 at HEAD 4520704).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hypercharm-provider", query: "trimZeros formatSpendHc", limit: 3 });
```

## Verdict
Adopt trimZeros verbatim and each ladder's threshold semantics as a set — flattening the asymmetry is the porting mistake this capsule exists to prevent. Adapt currency units and grouping locales. Omit hypercredit branding.
