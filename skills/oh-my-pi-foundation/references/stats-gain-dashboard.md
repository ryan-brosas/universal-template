<!-- capsule-v2 -->
# Stats gain-aggregator — savings ledger, worktree folding, zero-record tolerance

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Path:** `packages/stats/src/gain-aggregator.ts`. **Question:** How do you aggregate a per-run savings ledger into per-project dashboards without letting temp paths or nested worktrees distort buckets — and without failing when the ledger is absent?

**Path/Symbol:** `gain-aggregator.ts:getGainDashboardStats` (255+), `normalizeProjectPath` (68), `dedupeProjects` (93), `matchesProject` (48); `TEMP_PATH_RE` (22). DRIFT NOTE: the legacy v1 capsule's `aggregateGainStats` symbol is gone at HEAD — the dashboard entry is `getGainDashboardStats(range, project)` with path-normalization helpers extracted.
**Signature:** `getGainDashboardStats(range?, project?): Promise<GainDashboardStats>`; types `GainSourceTotals`, `GainTimeSeriesPoint` live in `shared-types.ts`; window config reused from `aggregator.ts:getTimeRangeConfig`.
**Data Shape:** savings source = `snapcompact-savings.jsonl` colocated next to `stats.db`; per-run rows of bytes/tokens (≈4 bytes/token); missing file → zero records, never an error.

### Decisive source
```ts
// Missing files are treated as zero records — never an error.
const TEMP_PATH_RE = /(?:^|\/)(?:T|tmp|pi-bash-exec|omp-bash-exec|pi-bash-detach)(?:\/|$)|^\/var\/folders(?:\/|$)/;
function matchesProject(cwd: string | undefined, project: string): boolean { … } // worktree roots fold to logical root
```

**Flow:** aggregates per-run savings into per-project totals + daily buckets; temp/internal paths (`/tmp`, exec/detach dirs, macOS `/var/folders`) are dropped; nested worktree cwds (e.g. `/repo/.worktrees/lane/src`) collapse onto their logical parent project via `normalizeProjectPath` BEFORE bucketing; the window uses the same `getTimeRangeConfig` as the rest of the dashboard. SQLite writes are chunked (~500 vars/statement) so one parameterized statement stays bounded.

**Invariant:** a missing ledger reads as zero, never throws; each row contributes to exactly one project bucket after the cwd-fold; nothing past the window is counted.

**Probe:** `test/gain-aggregator.test.ts`, `test/db-cost.test.ts`. Coverage caveat: tests excluded from graph index by design.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", name_pattern: "^(getGainDashboardStats|normalizeProjectPath|dedupeProjects|matchesProject)$", limit: 6, fields: ["signature"] });
```

## Verdict
Adopt missing-ledger-as-zero tolerance, temp-path exclusion before bucketing, and worktree→logical-root folding; adapt the jsonl row schema, token estimate, and window config to host; omit the OMP-specific temp-dir names unless porting the harness wholesale.
