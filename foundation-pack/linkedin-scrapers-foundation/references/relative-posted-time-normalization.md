<!-- capsule-v2 -->
# Relative posted-time normalization — how do I turn "3 weeks ago (Reposted)" into comparable datetimes without trusting LinkedIn's exact formatting?

**Source:** Auto_job_applier_linkedIn MIT `main@0ca5550f8aa80027621cfc17a30fceba05705f84`; Codebase Memory `Auto_job_applier_linkedIn`. **Question:** listing pages expose fuzzy relative ages, sometimes prefixed with "Reposted" — what is the minimal total parser that yields sortable datetimes and honest failures?

## Regex unit-table parser with coarse month/year approximations and None-on-miss
**Path/Symbol:** `modules/helpers.py:calculate_date_posted` (:180–203); caller `runAiBot.py` :938–947 (strips the "Reposted" prefix into a boolean BEFORE parsing; falls back to "Unknown" on failure).
**Signature:** `calculate_date_posted(time_string: str) -> datetime | None`.
**Data Shape:** input free text containing "<n> <unit>s ago"; output datetime.now() minus the mapped timedelta; months ≈ 30 days, years ≈ 365 days.

### Decisive source
```python
match = re.search(r'(\d+)\s+(second|minute|hour|day|week|month|year)s?\s+ago',
                  time_string.strip(), re.IGNORECASE)
if not match: return None                       # unparsable is DATA (None), not an exception
spans = {'second': timedelta(seconds=amount), 'minute': timedelta(minutes=amount),
         'hour': timedelta(hours=amount),   'day':   timedelta(days=amount),
         'week': timedelta(weeks=amount),   'month': timedelta(days=amount * 30),
         'year':  timedelta(days=amount * 365)}
return datetime.now() - delta if delta else None
# caller: if time_posted_text.__contains__("Reposted"): reposted = True; strip it first
```

**Flow:** top-card span text ("Reposted 2 weeks ago") → caller flags reposted and strips the prefix → parser regex-searches amount+unit+"ago" case-insensitively (singular or plural) → subtracts the unit table from now() → ledger stores a real datetime comparable across listings.
**Invariant:** approximation is DECLARED in one table (30/365) — good enough for sort/recency filtering, never presented as exact; any unparseable string returns None which the caller records as "Unknown" rather than guessing; "just now" (no number) honestly fails.
**Probe:** `tests/test_helpers.py::test_calculate_date_posted_units` — parametrized over all seven units with ±2-minute tolerance, plus case-insensitivity ("15 MINUTES AGO"), singular/plural agreement, and None for "just now"/"banana"/"" (:25–53). Executed this pass: test_helpers.py 19/19 passed.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Auto_job_applier_linkedIn", query: "calculate_date_posted", limit: 5 });
// → modules.helpers.calculate_date_posted modules/helpers.py :180-203 · tests/test_helpers.test_calculate_date_posted_units :34-37
```

## Verdict
Adopt the single-regex + declarative-span-table shape and the None-as-failure contract; adapt the unit table where your domain needs finer month math (calendar months via dateutil.relativedelta); omit LinkedIn-specific prefix handling by generalizing the "strip known decorations before parsing" step. Pairs naturally with duration-with-present (profile-side date kernel): both refuse to fabricate precision.
