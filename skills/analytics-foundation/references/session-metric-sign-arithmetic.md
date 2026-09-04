<!-- capsule-v2 -->
# Session metric sign arithmetic — how bounce rate, visit duration and views-per-visit survive CollapsingMergeTree negatives

**Source:** Plausible Analytics AGPL-3.0 `master@9cc669b9`; Codebase Memory `ext-analytics`. **Question:** Sessions live in a CollapsingMergeTree where updates are insert(sign=+1)+insert(sign=-1) pairs — what arithmetic keeps ratio metrics correct before and after merging?

## Metric-to-SQL ladder with defensive clamps
**Path/Symbol:** `lib/plausible/stats/sql/expression.ex:session_metric` (:419-500).
**Signature:** `session_metric(atom(), %Query{}) :: Ecto.Query.DynamicExpr` selected map fragment; every branch also emits `__internal_visits` when a downstream calculated metric needs it.
**Data Shape:** `sign ∈ {1,-1}`; `is_bounce`, `pageviews`, `events`, `duration` are per-row session snapshots; `greatest(..., 0)` and `ifNotFinite(..., 0)` clamp.

### Decisive source
```elixir
# :TRICKY: Before PR #4493, we could have sessions where `sum(is_bounce * sign)`
# is negative, leading to an underflow and >100% bounce rate. This works around that issue.
bounce_rate:
  fragment(
    "toUInt32(greatest(ifNotFinite(round(sumIf(is_bounce * sign, ?) / sumIf(sign, ?) * 100), 0), 0))",
    ^condition, ^condition),
```

**Flow:** bounce_rate = weighted mean of is_bounce over surviving rows; visits = `greatest(sum(sign), 0)`; pageviews/events = `greatest(sum(? * sign), 0)`; visit_duration = `round(sum(duration*sign)/sum(sign))`; views_per_visit = same ratio over pageviews.
**Invariant:** (1) Every ratio divides by `sum(sign)` — never by row count — because unmerged parts contain BOTH the old (−1) and new (+1) snapshot of each updated session; (2) unsigned underflow (`toUInt32(negative)`) is a real ClickHouse failure mode, hence double clamping `greatest(ifNotFinite(x, 0), 0)`; (3) bounce_rate's condition reuses the `event:page`→entry_page top-level filter so "bounce rate of page X" means "sessions that ENTERED at X".
**Probe:** `test/plausible/stats/query/query_test.exs` pins visit_duration non-smearing at :95-135; `grep -c 'greatest(ifNotFinite' lib/plausible/stats/sql/expression.ex` → 3 (:430/:477/:486).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-analytics", name_pattern: "^session_metric$", fields: ["lines"], limit: 5 });
```

## Smeared visits/visitors bypass sign sums
**Path/Symbol:** `lib/plausible/stats/sql/expression.ex:session_metric(:visits/…)` (:444-454).
**Flow:** when `query.smear_session_metrics`, visits = `scale_sample(uniq(s.session_id))` (uniq-based, bucket-safe); otherwise = `greatest(sum(sign), 0)` (cheap, exact only on merged data).
**Invariant:** uniq() over an unmerged sessions table still counts cancelled (−1) rows — but for smeared minute buckets the timeSlots expansion guarantees one row per alive session-bucket pair, making uniq the correct estimator. Mixing the two estimators in one query is the classic wrong-number bug.
**Probe:** `grep -c 'when query.smear_session_metrics' lib/plausible/stats/sql/expression.ex` → 3 (:117 time:hour sessions, :143 time:minute sessions, :444 smeared visits).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-analytics", name_pattern: "^event_metric$", fields: ["lines"], limit: 5 });
```

## Verdict
Adopt sign-arithmetic + clamp discipline for any CollapsingMergeTree-style table; adapt metric names; omit EE `scale_sample(_sample_factor)` wrappers if you have no sampling plane.
