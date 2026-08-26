<!-- capsule-v2 -->
# Sampling budget ladder — capping ClickHouse scans at 10M events with SAMPLE hints

**Source:** Plausible Analytics AGPL-3.0 `master@9cc669b9` (`extra/lib/plausible/stats/sampling.ex`, EE-only file); Codebase Memory `ext-analytics`. **Question:** How does the engine decide to sample a query, what fraction does it pick, and how do sampled results stay honest?

## Fraction decision closure
**Path/Symbol:** `extra/lib/plausible/stats/sampling.ex:fractional_sample_rate/2` (:76-93), `estimate_traffic/3` (:118+).
**Signature:** `fractional_sample_rate(traffic_30_day :: pos_integer() | nil, query) :: :no_sampling | float()` — `@default_sample_threshold 10_000_000`.
**Data Shape:** inputs are 30-day traffic estimate (from `SamplingCache`) and the parsed query; outputs `:no_sampling` or a fraction ≥ `min_sample_rate()` = **0.013**, rounded to 2 decimals.

### Decisive source
```elixir
fraction = if estimated_traffic > 0,
  do: Float.round(@default_sample_threshold / estimated_traffic, 2), else: 1.0

cond do
  duration < 1      -> :no_sampling   # don't sample small time ranges
  fraction > 0.4    -> :no_sampling   # insignificant effect ⇒ skip
  true              -> max(fraction, min_sample_rate())
end
```

**Flow:** estimated events = daily traffic × queried days × `@filter_traffic_multiplier^min(filters, 2)` where multiplier = **1/4** — each filter is assumed to quarter traffic, capped at 2 filters; duration days = `round(diff_seconds / 86_400)` (inclusive-range rounding, documented) clamped by site's native stats start.
**Invariant:** (1) Sampling never applies below 1 day or above 40% fraction — the two guards bound distortion; (2) `sample_percent` metric surfaces honesty to users via `if(any(_sample_factor) > 1, round(100/any(_sample_factor)), 100)` — every metric wraps through `scale_sample(× any(_sample_factor))` so numbers stay absolute; (3) sessions range WHERE keeps the redundant primary-key lower bound precisely so `_sample_factor` estimation has minimal skew (see where-builder capsule).
**Probe:** `grep -c 'defp estimate_by_filters\|@filter_traffic_multiplier' extra/lib/plausible/stats/sampling.ex` → 3 (:126 defp + :124 attr + :129 use); `grep -n 'min_sample_rate(), do: 0.013' extra/lib/plausible/stats/sampling.ex`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-analytics", name_pattern: "^add_query_hint$", fields: ["lines"], limit: 5 });
```

## Hint injection point
**Path/Symbol:** `add_query_hint(db_query, threshold)` (:43-46): `from(x in query, hints: unsafe_fragment(^"SAMPLE #{threshold}"))` — called from `SQL.QueryBuilder.build_table_query` on BOTH table queries AND their join subqueries.
**Flow:** `put_threshold(query, site, params)` runs during QueryBuilder.build (EE branch) BEFORE optimize/split; `"infinite"` param maps to `:no_sampling` sentinel.
**Invariant:** The hint must ride every subquery touching rows or metrics mix sampled and full data. CE builds compile this whole module out (`on_ee`) — porters of CE-only trees must strip callsites, not stub them.
**Probe:** `grep -c 'add_query_hint' lib/plausible/stats/sql/query_builder.ex` → 4 (:44/:64/:96/:122).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-analytics", qn_pattern: "stats.sampling", fields: ["lines"], limit: 8 });
```

## Verdict
Adopt budget-fraction sampling with honesty multipliers; adapt threshold constant; omit if your warehouse can't attach SAMPLE hints per subquery.
