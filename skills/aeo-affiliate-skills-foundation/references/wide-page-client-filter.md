<!-- capsule-v2 -->
# Wide-page client-side filter adapter — how do you support filters the upstream API cannot evaluate server-side?

**Source:** aeo-affiliate-skills MIT `main@ed17ef37bc167b52d9596cbe0292507f001c483d`; Codebase Memory `aeo-affiliate-skills`. **Question:** The API only accepts `q`, `sort`, `limit` — where do `reward_type`/`tags`/`min_cookie_days` get applied, and how do you avoid filtering an already-too-small page into nothing?

## Widen the page, filter locally, slice back to the requested limit
**Path/Symbol:** `tools/src/api.ts`:`fetchPrograms` (129–164), `applyClientFilters` (109–127), `adapt` (85–107), `REWARD_TYPE_ALIASES` (77–83); sibling `fetchProgram` (166–183).
**Signature:** `async function fetchPrograms(params: SearchParams, _apiKey?: string): Promise<ProgramsResponse>`; `function applyClientFilters(programs: Program[], params: SearchParams): Program[]`; `function adapt(p: OAProgram): Program`.
**Data Shape:** Raw upstream shape `OAProgram` is camelCase with nested `commission?: {type?, rate?}`, `cookieDays?`, `stars?`, `shortDescription?`. Normalized `Program` is flat snake_case (`reward_type`, `reward_value`, `cookie_days`, `stars_count`, …) with defaulted fields (`stars ?? 0`, `views_count: 0`, `status: "published"`, `type: "affiliate_program"`). Response `{data, count}`; count falls back `json.total ?? data.length`.

### Decisive source
```ts
const hasClientFilter = !!(params.reward_type || params.tags || params.min_cookie_days);
...
// When filtering client-side, pull a wider page so the filter has data to work on.
const fetchLimit = hasClientFilter ? Math.max(limit ?? 10, 100) : limit;
if (fetchLimit) url.searchParams.set("limit", String(fetchLimit));
...
if (hasClientFilter) {
  data = applyClientFilters(data, params);
  if (limit) data = data.slice(0, limit);
  return { data, count: data.length };
}
return { data, count: json.total ?? data.length };
```

Filter semantics inside `applyClientFilters`:

```ts
const want = (REWARD_TYPE_ALIASES[params.reward_type] ?? params.reward_type).toLowerCase();
out = out.filter((p) => (p.reward_type ?? "").toLowerCase().includes(want));
...
if (params.min_cookie_days) {
  out = out.filter((p) => (p.cookie_days ?? 0) >= params.min_cookie_days!);
}
```

**Flow:** detect client-only filters → widen fetch page to at least 100 → adapt each raw item to the normalized shape → apply reward alias + substring-lowercase match, comma-separated ANY-match on tags, numeric cookie floor where `null → 0` (excluded when the filter is active) → slice to the caller's limit. Non-OK responses throw `API error (${status}): ${body}`; the daemon maps that to HTTP 502 with the formatted error body. `fetchProgram` (single slug route) maps 404 → `null` instead of throwing, other statuses throw.
**Invariant:** Client-side filters are evaluated over a WIDER page than the user asked for and only afterwards truncated to it. Filtering first-page-of-10 data would routinely return zero rows for common filters; widening to ≥100 then slicing preserves both recall and the requested page size. Keep the two vocabulary maps separate: `REWARD_TYPE_ALIASES` exists to translate the CLI vocabulary into words that appear in upstream commission strings ("cps_recurring"→"recurring"), while `format.ts`'s `typeMap` renders display labels ("cpl"→"per lead") — merging them corrupts one side.
**Probe:** Repository-owned contract suite pins this seam end-to-end: `bun run tests/test-doc-contracts.ts` asserts `api.ts` reads raw `commission`/`cookieDays`/`stars` AND produces normalized `reward_value`/`reward_type`/`cookie_days`/`stars_count`, points at `openaffiliate.dev/api`, and does NOT contain the retired host `list.affitor.com`. Executed GREEN (verification.md P2). Source pin: `grep -n "Math.max(limit" tools/src/api.ts` → :140.
**Coverage caveat:** none — `tools/src/api.ts` checked `no_recorded_issue` at generation 2026-08-25T08:24:56Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aeo-affiliate-skills", query: "applyClientFilters adapt fetchPrograms normalized Program", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt wide-page-then-filter-then-slice for any upstream lacking server-side filtering, the camelCase→snake_case adapter with explicit field defaults, and the 404→null vs throw split between list and detail lookups. Adapt the alias table to your provider's actual commission vocabulary (verify against live response shapes before extending). Omit the vestigial `_apiKey` parameter — kept so callers don't change signature after moving from a keyed API to the public one; drop it in a greenfield port.
