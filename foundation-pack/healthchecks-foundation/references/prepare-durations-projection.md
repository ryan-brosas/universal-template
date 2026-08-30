<!-- capsule-v2 -->
# prepare_durations batch projection — N+1 elimination with an honest degrade switch

**Source:** healthchecks BSD-3-Clause `master@29b5ec25`; Codebase Memory `healthchecks`. **Question:** How do you display per-ping job durations for a page of pings without issuing one SQL query per ping — and give up gracefully when the data doesn't support it?

## prepare_durations + Ping.duration
**Path/Symbol:** `hc/api/models.py:prepare_durations` (:834-882), `Ping.duration` (:808-826), `hc/lib/s3.py` sibling; consumers `hc/api/views.py:pings` (:596-620), `hc/front/views.py:_get_events` (:909-956).
**Signature:** `prepare_durations(pings: Sequence[Ping]) -> None` (mutates in place; input MUST be newest-first); `Ping.duration` property = the per-instance SQL fallback.
**Data Shape:** Walks with `starts: dict[rid | None, datetime | None]`; sentinel progression: absent → datetime (seen start) → None (consumed). Constants: MAX_DURATION = 72h, miss budget = 10.

### Decisive source
```python
# hc/api/models.py — reverse scan, rid-keyed start matching
for ping in reversed(pings):          # oldest → newest, guarded by assert on ids
    if ping.kind == "start":
        starts[ping.rid] = ping.created
    elif ping.kind in (None, "fail"):
        if ping.rid not in starts:
            if ping.created - earliest.created >= MAX_DURATION:
                ping.duration = None            # too far back to ever match: stop caring
            else:
                num_misses += 1                 # maybe a start exists further in history...
        else:
            ping.duration = None
            start = starts[ping.rid]
            if start and (ping.created - start) < MAX_DURATION:
                ping.duration = ping.created - start
        starts[ping.rid] = None                 # a success/fail CONSUMES the run

if num_misses > 10:
    for ping in pings:
        ping.duration = None                    # disable duration display altogether
```

**Flow:** Caller fetches one page newest-first (`order_by("-id")`, `defer("body_raw")`, optionally `annotate(body_raw_length=Length("body_raw"))` so has_body() works without the blob) and calls prepare_durations. The scan matches each terminal event to its open "start" by exact rid; consecutive successes with no start consume nothing new. Misses (terminal events whose start would live below the page) count toward the budget; exceeding it nulls EVERY duration rather than falling back to per-ping queries.
**Invariant:** The function is only correct on descending input — it asserts id monotonicity and upstream tests pin AssertionError on ascending lists (`test_it_requires_pings_in_descending_time_order`). A consumed `starts[rid] = None` distinguishes "run closed" from "never opened"; dropping that line double-counts runs across consecutive successes. The >10-miss kill switch trades a feature for bounded latency and is enforced by assertNumQueries in BOTH API and front suites (4 queries total, no per-ping fallback).
**Probe:** `hc/api/tests/test_ping_model.py::test_it_matches_start_event_by_rid` (two interleaved runs A/B resolve independently), `test_it_handles_consecutive_success_signals` (only first gets duration), `test_it_caps_misses` (15 unique rids → all None), `hc/api/tests/test_get_pings.py::test_it_calculates_overlapping_durations` (assertNumQueries(4)), `hc/front/tests/test_get_events.py::test_it_disables_duration_display`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "healthchecks", query: "prepare_durations duration MAX_DURATION rid", limit: 10 });
```
Resolves line-exact: prepare_durations :834-882 and its test class PrepareDurationsTestCase.

## Verdict
Adopt the single-pass rid-keyed scan with consumption semantics, the MAX_DURATION short-circuit, and the honest whole-page degrade. Adapt the 72h cap and 10-miss budget to your page size. Omit the assert if you can't guarantee ordering — but then you own whatever wrong durations result.
