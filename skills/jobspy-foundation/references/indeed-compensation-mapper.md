<!-- capsule-v2 -->
# Indeed structured-compensation mapper — how do GraphQL compensation payloads become Compensation without the string parser, and which source wins when both baseSalary and estimated exist?

**Source:** JobSpy MIT `main@fda080a373e8`; Codebase Memory `JobSpy`. **Question:** When Indeed returns a structured compensation object, what is the preference order between baseSalary and estimated.baseSalary, where does currency come from, and what happens to unknown unitOfWork values?

## Indeed GraphQL compensation plane
**Path/Symbol:** `jobspy/indeed/util.py:get_compensation` (:20–49), `jobspy/indeed/util.py:get_compensation_interval` (:71–83); call site `jobspy/indeed/__init__.py:230` (`compensation=get_compensation(job["compensation"])`).
**Signature:** `get_compensation(compensation: dict) -> Compensation | None`; `get_compensation_interval(interval: str) -> CompensationInterval`.
**Data Shape:** input keys `baseSalary`, `estimated{baseSalary,currencyCode}`, `currencyCode`; salary entries carry `unitOfWork` (`HOUR|DAY|WEEK|MONTH|YEAR`) and `range{min,max}`. Output `Compensation(interval, min_amount, max_amount, currency)` or None.

### Decisive source
```python
if not compensation["baseSalary"] and not compensation["estimated"]:
    return None
comp = (compensation["baseSalary"]
        if compensation["baseSalary"]
        else compensation["estimated"]["baseSalary"])
interval = get_compensation_interval(comp["unitOfWork"])   # raises ValueError on unknown
min_range = comp["range"].get("min"); max_range = comp["range"].get("max")
return Compensation(
    interval=interval,
    min_amount=int(min_range) if min_range is not None else None,   # truncation, not rounding
    max_amount=int(max_range) if max_range is not None else None,
    currency=(compensation["estimated"]["currencyCode"]
              if compensation["estimated"] else compensation["currencyCode"]),
)
# get_compensation_interval: {DAY:DAILY, YEAR:YEARLY, HOUR:HOURLY, WEEK:WEEKLY, MONTH:MONTHLY}
#   mapped in CompensationInterval.__members__ else raise ValueError(f"Unsupported interval: {interval}")
```

**Flow:** both-empty guard -> pick baseSalary ELSE estimated.baseSalary for AMOUNTS -> strict interval table (raise on unknown) -> int()-truncate range ends -> currency from estimated.currencyCode whenever estimated exists, else top-level currencyCode.
**Invariant:** amounts prefer baseSalary but CURRENCY prefers estimated — the two come from different sources when both blocks exist (executed: baseSalary HOUR payload kept CAD currency). Unknown unitOfWork RAISES ValueError, so the following `if not interval: return None` is unreachable dead code. Contrast: Glassdoor's `parse_compensation` (glassdoor/util.py:4–23, cross-ref glassdoor-adapter.md) floor-truncates p10/p90 percentiles via `// 1`, special-cases ANNUAL->YEARLY then delegates to the model classmethod; it returns None on falsy adjusted_pay but TypeErrors on a non-empty dict missing p90 (executed). A third mapper, `CompensationInterval.get_interval` (model.py:210–224), maps only YEAR/HOUR plus member fallback and returns STRING values — three interval mappers disagree by design.
**Probe:** no in-repo runner (recorded block). Executed byte-for-byte against standalone-loaded jobspy/model.py (pydantic OK): base-pref HOUR 30.9/55.4 -> HOURLY 30.0/55.0 USD; est-fallback YEAR 70000.5/90000.9 -> YEARLY 70000.0/90000.0 GBP; both-empty -> None; unitOfWork CENTURY -> ValueError 'Unsupported interval'; glassdoor ANNUAL 123456.7/234567.2 -> YEARLY 123456.0/234567.0 EUR; missing p90 -> TypeError.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "JobSpy", query: "get_compensation get_compensation_interval unitOfWork baseSalary estimated", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the split-provenance rule (amounts from primary block, currency from enriched block when present), strict raise-on-unknown unit mapping, and int() truncation of range ends. Adapt currency selection to your host's trust model (you may prefer baseSalary.currencyCode when present). Omit the unreachable None-guard and the dead Glassdoor percentile path unless you port that payload shape too. Coverage caveat: check_index_coverage no_recorded_issue; behavior pinned by executed excerpts, not an in-repo test suite.