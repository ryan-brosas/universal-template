<!-- capsule-v2 -->
# Pool-health & session-status reporting — how do you render live rotation health that can never disagree with actual selection behavior?

**Source:** pi-multi-pass (package.json declares MIT; NO LICENSE/COPYING file at pin — citations-only) `main@b9d9d1d7a09252a19ec79868517d49d4f07c4760`; Codebase Memory project `pi-multi-pass` (FULL, 402 nodes / 1495 edges, cluster 48). **Question:** when a dashboard or status line must show which accounts are usable right now, how does the source keep that display truthful without duplicating eligibility logic?

## Reporting plane (cluster 48): pure reporters over the SAME predicates the planner uses
**Path/Symbol:** `extensions/multi-sub.ts`: `summarizePoolHealth` (4169-4209), `formatPoolStatusLines` (4221-4265), `getChainEntryIssue` (4291-4307, classifier reused from the failover-plan capsule), `formatFailoverStatus` (4359-4374), `formatChainEntryStatus` (4461-4479), `formatChainStatusLines` (4517-4560); schedule predicates shared with the strategy plane: `getDayOfWeek` (1942-1944), `isInHourRange` (1946-1954), `isInDateRange` (1956-1961), `isInScheduleWindow` (1963-1974), `getWindowRemainingMs` (1978-1989), `getScheduledMemberState` (1998-2027).
**Signature:** `function summarizePoolHealth(pool: PoolConfig, authStorage: { hasAuth(provider: string): boolean }, poolManager: Pick<PoolManager, "getAvailableMembers" | "isMemberExhausted">): { availableCount; authedCount; memberCount; unavailableCount; statusLabel }`; `formatChainStatusLines(chain, config?, authStorage?, poolManager?): string[]`.
**Data Shape:** every reporter takes a STRUCTURAL subset of PoolManager (`Pick<..., "getAvailableMembers" | "isMemberExhausted">`) plus a one-method authStorage duck type — no PoolManager instance, no mutation. Chain reporters take trailing OPTIONAL dependencies: with none they still render structure; with `config` only they count invalid entries; with all three they additionally compute "usable entries now".

### Decisive source
```ts
const availableMembers = pool.enabled
	? poolManager.getAvailableMembers(pool, authStorage)
	: [];
let authedCount = 0;
for (const member of pool.members) {
	if (authStorage.hasAuth(member)) authedCount += 1;
}
...
if (!pool.enabled) {
	statusLabel += " | pool disabled";
} else if (memberCount === 0) {
	statusLabel += " | no members configured";
} else if (availableCount === 0) {
	if (authedCount === 0) {
		statusLabel += " | no auth";
	} else {
		statusLabel += " | cooldown/no eligible members";
	}
}
```
```ts
function isInHourRange(hour: number, range: [number, number]): boolean {
	const [start, end] = range;
	if (start <= end) {
		return hour >= start && hour < end;
	}
	// Wrapping range, e.g. [22, 6] = 22:00-05:59
	return hour >= start || hour < end;
}
```

**Flow:** `summarizePoolHealth` computes counts then resolves ONE diagnostic label by a fixed ladder — pool disabled beats no-members beats zero-available; zero-available splits into "no auth" vs "cooldown/no eligible members" using authedCount, because getAvailableMembers cannot distinguish those causes. `formatPoolStatusLines` renders the header block (name/enabled, baseProvider, strategy defaulting to "round-robin", summary label), then per member composes `logged in/not logged in` + `(rate limited, cooling down)` / `(available)` / `(pool disabled)` + `[role]` + `(in window)/(outside window)` via `getScheduledMemberState`. `formatChainStatusLines` rolls up per chain: invalidEntries counted through `getChainEntryIssue`, usableEntries = enabled ∧ no-issue ∧ owning-pool-enabled ∧ `summarizePoolHealth(...).availableCount > 0`, printed as `usable entries now: N/M` only when full dependencies were supplied. `formatFailoverStatus` projects a FailoverCandidate to `chain:<name>#<index+1> | active <target>` or `pool:<name> | ...`; `PoolManager.handleError` calls it ITSELF at multi-sub.ts:2690/2701/2712 (exhausted: `cascade exhausted | no eligible target`) and :2725 (after a successful switch), so the status line is written by the same code path that rotated.

**Invariant:** display truthfulness by construction — reporters call the exact predicates the planner uses (`getAvailableMembers`, `isMemberExhausted`, `isInScheduleWindow`), never re-implement eligibility, and never mutate config or PoolState; a disabled pool reports availability 0 while still surfacing authedCount so the cause stays visible; schedule semantics are identical in strategy and status planes because both share `isInScheduleWindow` (wrapping `[22,6]` hours supported; `getScheduledMemberState` treats missing schedule, empty windows, and role "overflow" as always-active with `shortestRemainingMs: Infinity`; `getWindowRemainingMs` adds 24h when a wrapped window's end time has already passed today).

**Probe:** `tests/runtime-failover-check.mjs` `runSessionStatusChecks` (659-682) pins the harness twin `renderSessionStatus` (646-657): first enabled chain's first enabled entry renders `chain:ordered-fallback | starts primary -> claude-sonnet-4`; disabling the chain or all entries yields null. Executed green at pin together with all six check scripts and the --retry-start-turn/--pool-only/--no-loop/--failure-path modes.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-multi-pass", query: "summarizePoolHealth formatPoolStatusLines formatChainStatusLines", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt the reporter decomposition: count layer (summarize), member layer (format lines), roll-up layer (chain totals), each taking narrow structural types so any host can supply its own auth/pool implementations; adopt the fixed diagnostic-label ladder and the shared-predicate invariant (render with the planner's own functions, never a parallel implementation); adopt the wrapping-hour algebra verbatim. Adapt label strings, status transport (here pi `ui.select`/`ui.setStatus`), and the FailoverCandidate projection to your host's surface. Omit pi TUI command handlers (`handlePoolStatus`, `handleSubsStatus`) and the quota-picker UI plane (`selectQuotaResult`/`buildQuotaSelectItems` — host `showWrappedSelect` transport over the already-capsuled `compareQuotaResults` ordering). Coverage caveat: `runSessionStatusChecks` exercises the harness twin `renderSessionStatus`, not the source `formatChainStatusLines` directly; the source functions were verified by byte-identical direct reads at the pin, and no upstream check drives the schedule-window branch of `formatPoolStatusLines` (same runner-honesty caveat as the strategy seam).
