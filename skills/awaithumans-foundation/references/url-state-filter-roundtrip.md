<!-- capsule-v2 -->
# URL-State Filter Round-Trip — the query string is the single source of truth for operator list state

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** How should a React list page keep filters/pagination in the URL so refresh-and-share-a-link works, without trusting anything the URL carries?

## Connected graph-selected seam
**Path/Symbol:** `packages/dashboard/app/(dashboard)/page.tsx` — `readFiltersFromSearchParams` (:58-78) / `filtersToSearchParams` (:80-90) / `updateFilters` (:115-133); twin pair duplicated in `packages/dashboard/app/(dashboard)/audit/page.tsx` (:53-71/:73-82).
**Signature:** `readFiltersFromSearchParams(params: URLSearchParams): FilterState` / `filtersToSearchParams(state: FilterState): URLSearchParams` / `updateFilters(patch: Partial<FilterState>)`.
**Data Shape:** `FilterState { status: TaskStatus|"all"; assignedTo: string; unassigned: boolean; mine: boolean; pageSize: number; offset: number }`.

### Decisive source
```ts
const rawStatus = params.get("status") ?? "all";
const status = STATUS_OPTIONS.some((o) => o.value === rawStatus)
    ? (rawStatus as TaskStatus | "all")
    : "all";
const rawSize = Number(params.get("pageSize") ?? TASK_LIST_DEFAULT_PAGE_SIZE);
const pageSize = TASK_LIST_PAGE_SIZES.includes(rawSize)
    ? rawSize
    : TASK_LIST_DEFAULT_PAGE_SIZE;
const offset = Math.max(0, Number(params.get("offset") ?? "0") || 0);
```
Write side omits defaults (:80-90): only non-default status/assignedTo/unassigned/mine/pageSize/offset are set. Patch side snaps (:120-124):
```ts
// Mutating filters (status / mine / etc.) snaps offset back
// to 0 — staying on page 5 of a different filter is rarely
// what the user wants and breaks "Next is empty" detection.
const offsetBumped = "offset" in patch && patch.offset !== undefined;
const next: FilterState = { ...filters, ...patch,
    offset: offsetBumped ? (patch.offset as number) : 0 };
...
router.replace(query ? `/?${query}` : "/", { scroll: false });
```

**Flow:** every render reads the URL → `useMemo` FilterState; user action → patch → serialize-with-defaults-omitted → `router.replace(..., {scroll:false})` (back button stays clean); poll interval re-runs loadTasks from current filters. Request precedence (:142-149): `unassigned=true` wins; else `mine` → `assigned_to = me.email` (/me fetched ONCE :159-164); else explicit `assignedTo`. Pagination is TOTAL-LESS: `hasNextPage = tasks.length === filters.pageSize` (:172-176).
**Invariant:** READ allowlists everything (status ∈ STATUS_OPTIONS else "all"; pageSize ∈ TASK_LIST_PAGE_SIZES else default; offset clamped ≥0 via `Number(x)||0`) because the URL is attacker/wearer-editable input; WRITE omits defaults so URLs stay clean and shareable. The audit twin hardcodes `unassigned:false` purely to keep `<TaskFilterBar>` shareable (terminal tasks are past assignment). No total count is fetched anywhere — an empty "Next" is detected by short-page.

**Probe:** no vitest suite exists for dashboard pages (node_modules never provisioned — recorded caveat; deterministic line-checks used). Server-side counterparts pinned by `test_route_authorization.py` scoping tests (:180-220). Source anchors verified byte-exact at pin: allowlist parse :58-78, omit-defaults write :80-90, snap-back :115-133, precedence :142-149, hasNextPage :172-176.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "filters from search params allowlist status page size offset update filters", limit: 6 });
```
Live at pin: all four twins rank 1-4 — page.tsx readFilters −46.9 (:58-78), audit readFilters −45.82 (:53-71), page.tsx filtersTo −41.71 (:80-90), audit filtersTo −40.77 (:73-82); TaskFilterBar family close behind (−25.4).

## Verdict
Adopt URL-as-state with the allowlist-read / omit-defaults-write / offset-snap-on-patch triple; adopt total-less pagination when your API can't cheaply COUNT under arbitrary filters. Adapt option lists to your domain. Omit the audit-style hardcoded flag only if your shared component takes per-context prop defaults instead.
