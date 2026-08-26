<!-- capsule-v2 -->
# Strategy reorder fail-open — how do quota/schedule/custom selection strategies degrade without breaking failover?

**Source:** pi-multi-pass MIT-declared per package.json (no LICENSE file at pin; citations-only) `main@b9d9d1d7a09252a19ec79868517d49d4f07c4760`; Codebase Memory `pi-multi-pass`. **Question:** How can optional "pick smart" policies (quota data, time windows, user scripts) improve candidate order WITHOUT ever being able to break or stall the failover itself?

## Strategies only reorder validated candidates; every failure keeps default order
**Path/Symbol:** `extensions/multi-sub.ts`: `PoolManager.reorderCandidatesByStrategy` (2478-2573), `getQuotaBestMember` (2439-2472), `getScheduledMemberOrder` + `getScheduledMemberState` (1998-2050), `runCustomSelector` (2093-2127), `loadSelectorScript` (2068-2091).
**Signature:** `private async reorderCandidatesByStrategy(pool: PoolConfig, plan: FailoverPlan, currentModel: Model<Api>, ctx: ExtensionContext, cascade: FailoverCascadeState, lastUserPrompt: string | null): Promise<void>`; `async getQuotaBestMember(...): Promise<string | undefined>`.
**Data Shape:** PoolStrategy = "round-robin" | "quota-first" | "scheduled" | "custom"; strategy mutates ONLY plan.candidates order in place.

### Decisive source
```ts
const strategy = pool.strategy || "round-robin";
if (strategy === "round-robin") return;
const poolCandidates = plan.candidates.filter((c) => c.source === "pool" && c.poolName === pool.name);
if (poolCandidates.length < 2 && strategy !== "custom") return;
if (strategy === "quota-first") {
	try {
		const best = await this.getQuotaBestMember(pool, currentModel.provider, ctx.modelRegistry.authStorage, cascade.attemptedProviders);
		if (best) {
			const bestIdx = plan.candidates.findIndex((c) => c.provider === best && c.source === "pool");
			if (bestIdx > 0) { const [moved] = plan.candidates.splice(bestIdx, 1); plan.candidates.unshift(moved); }
		}
	} catch { /* Quota check failed -- proceed with default order. */ }
	return;
}
// scheduled: getScheduledMemberOrder rebuilds pool candidates in schedule order, chain candidates kept at end.
// custom: runCustomSelector result must be a member of AVAILABLE else ignored; try/catch falls back to default order.
```

**Flow:** round-robin = no-op -> fewer than 2 pool candidates = nothing to reorder -> quota-first asks network quota checkers for the best member and MOVES it to the front only if it is already a validated pool candidate -> scheduled sorts preferred-in-window members by SHORTEST remaining window ms (wrapping hour ranges like [22,6] supported), then defaults, then overflow roles; preferred-but-out-of-window members are dropped entirely; chain candidates stay appended at the end -> custom loads (and caches) a user JS module whose returned string/array must intersect the available set, first valid hit wins -> ANY throw, undefined result, or missing data leaves the planner's default order intact.
**Invariant:** a strategy can only PROMOTE or REORDER among candidates that already passed eligibility; it can never introduce, remove (except out-of-window preferred under "scheduled"), or block a candidate; all strategy code paths are wrapped so failover latency and correctness never depend on quota APIs or user scripts.
**Probe:** `node tests/subscription-limits-check.mjs` (pins the quota-check data layer feeding quota-first; green at b9d9d1d7a092). COVERAGE CAVEAT: no upstream check script exercises reorderCandidatesByStrategy/scheduled/custom directly (grep over tests/ finds zero matches); the RuntimeHarness twin omits this step — treat strategy behavior as source-read-only until upstream adds checks.
**Coverage note:** extensions/multi-sub.ts indexed FULL with no_recorded_issue; the cited ranges were read directly from source at the pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-multi-pass", query: "reorderCandidatesByStrategy getQuotaBestMember runCustomSelector", limit: 10, fields: ["signature"] });
```

## Verdict
Adopt the fail-open shape: strategies as pure reorder hints over pre-validated candidates, single-candidate shortcut before any network call, result-validation against the available set. Adapt quota checking behind your own capability interface (upstream calls runQuotaChecks). Omit arbitrary user-JS selector execution unless you can sandbox it.