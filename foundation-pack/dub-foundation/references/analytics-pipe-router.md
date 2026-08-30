<!-- capsule-v2 -->
# Analytics pipe router — three-way pipe map plus the dual filter-channel split

**Source:** dub AGPL-3.0-or-later `main@29df217a29631ced4041882a28d2327cc4546f27`; Codebase Memory `dub`. **Question:** Which Tinybird pipe serves a given groupBy, and which filters ride top-level params versus the JSON filters blob?

## Pipe selection + two filter channels
**Path/Symbol:** `apps/web/lib/analytics/get-analytics.ts` :80-196 (pipe map :99-111; metadata parse :125; identity extraction :156-162; param assembly :164-194).
**Signature:** internal to `getAnalytics(params)`; emits `tb.buildPipe({ pipe, parameters: analyticsFilterTB, data })` then `pipe(tinybirdParams)`.
**Data Shape:** identity filters become paired `<name>`/`<name>Operator` top-level params (operator collapsed to `IN`|`NOT IN`); event dims ride ONE `filters` JSON string; window rides `start`/`end` (`formatUTCDateTimeClickhouse`) + `granularity`.

### Decisive source
```ts
const pipe = tb.buildPipe({
  pipe: ["count", "timeseries"].includes(groupBy!)
    ? `v4_${groupBy}`
    : [
        "top_folders", "top_link_tags", "top_domains",
        "top_partners", "top_partner_tags", "top_groups",
      ].includes(groupBy!)
    ? "v4_group_by_link_metadata"
    : "v4_group_by",
  ...
});
...
filters: allFilters.length > 0 ? JSON.stringify(allFilters) : undefined,
```
(get-analytics.ts :99-111 condensed; :193)

**Flow:** `trigger` renamed `triggers` first (:80) → three-way pipe map → `metadataQueryParser(query)` output merged ahead of `buildAdvancedFilters` output into `allFilters` (:125-133) → `extractWorkspaceLinkFilters` splits link/domain/folder/tag/partner/partnerTag/group/tenant into TOP-LEVEL params → single `pipe(tinybirdParams)` call.
**Invariant:** the two channels are NOT interchangeable — identity filters execute at Tinybird's `workspace_links` node BEFORE event joins (their comment says so verbatim), while the JSON `filters` channel applies event-level predicates; the JSON channel's field set is closed (15-field `SUPPORTED_FIELDS` whitelist), so new dimensions require a code change, never user input.

**Probe:** executed: `grep -n 'v4_group_by_link_metadata' ...` → :110; `grep -n 'metadataQueryParser(query)' ...` → :125; `grep -n 'filters: allFilters.length' ...` → :193. Test anchor: `tests/analytics/get-analytics-advanced.test.ts` (:1-349, CI-gated integration; e.g. IS-NOT exclusion case :68-88).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", name_pattern: "^(buildAdvancedFilters|ensureParsedFilter|prepareFiltersForPipe|extractWorkspaceLinkFilters)$", file_pattern: "*filter-helpers.ts", limit: 8 });
```
(observed: four functions at filter-helpers.ts :30-60/:69-81/:90-134/:161-178.)

## Verdict
Adopt the three-way pipe map and the strict two-channel split with a closed field whitelist. Adapt pipe naming/versioning to your warehouse. Omit the specific v4 pipe bodies (not in this repo).
