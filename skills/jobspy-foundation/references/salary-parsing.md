<!-- capsule-v2 -->
# Salary & number parsing — threshold-based interval inference, locale-safe currency parsing, annualization

**Source:** JobSpy MIT `main@fda080a`; Codebase Memory `JobSpy`. **Question:** How does JobSpy parse salary strings and currency into interval + min/max + annualized values without ever guessing badly?

## Salary extraction
**Path/Symbol:** `jobspy/util.py` — `extract_salary` (211–278), `currency_parser` (188–202), `convert_to_annual` (311–324), `extract_job_type` (281–297), `extract_emails_from_text` (170–174), `get_enum_from_job_type` (177–185), `get_enum_from_value` (304–308), `map_str_to_site` (300–301), `desired_order` (327–363).
**Signature:** `extract_salary(salary_str, lower_limit=1000, upper_limit=700000, hourly_threshold=350, monthly_threshold=30000, enforce_annual_salary=False) -> (interval, min, max, "USD") | (None,None,None,None)`. `currency_parser(cur_str) -> float`. `convert_to_annual(job_data: dict)`.
**Data Shape:** `extract_salary` returns a 4-tuple; on ANY failure it returns `(None, None, None, None)` — it refuses to guess. `convert_to_annual` mutates a `job_data` dict in place (scales by 2080/12/52/260 and sets `interval="yearly"`).

### Decisive source
```python
def currency_parser(cur_str):
    cur_str = re.sub("[^-0-9.,]", "", cur_str)
    cur_str = re.sub("[.,]", "", cur_str[:-3]) + cur_str[-3:]   # strip thousands separators from integer part only
    if "." in list(cur_str[-3:]): num = float(cur_str)
    elif "," in list(cur_str[-3:]): num = float(cur_str.replace(",", "."))
    else: num = float(cur_str)
    return np.round(num, 2)

def extract_salary(salary_str, lower_limit=1000, upper_limit=700000, hourly_threshold=350, monthly_threshold=30000, enforce_annual_salary=False):
    min_max_pattern = r"\$(\d+(?:,\d+)?(?:\.\d+)?)([kK]?)\s*[-—–]\s*(?:\$)?(\d+(?:,\d+)?(?:\.\d+)?)([kK]?)"
    match = re.search(min_max_pattern, salary_str)
    if match:
        min_salary, max_salary = to_int(match.group(1)), to_int(match.group(3))
        if "k" in match.group(2).lower() or "k" in match.group(4).lower():
            min_salary *= 1000; max_salary *= 1000
        if min_salary < hourly_threshold:      interval = HOURLY; annual_min = min*2080
        elif min_salary < monthly_threshold:   interval = MONTHLY; annual_min = min*12
        else:                                  interval = YEARLY; annual_min = min
        if not annual_max_salary: return None,None,None,None
        if (lower_limit <= annual_min <= upper_limit and lower_limit <= annual_max <= upper_limit
                and annual_min < annual_max):
            if enforce_annual_salary: return interval, annual_min, annual_max, "USD"
            else: return interval, min_salary, max_salary, "USD"
    return None, None, None, None
```

**Flow:** `currency_parser` strips non-numeric chars, then removes thousands separators from the integer part only (preserving the decimal separator in the last 3 chars), then detects comma-vs-dot decimal. `extract_salary` matches a `$min–$max` range with optional `k` suffix per side; infers interval by thresholds (`<350` hourly, `<30000` monthly, else yearly); annualizes ×2080/×12; enforces a sanity window `[1000, 700000]` and `min < max`; returns the raw or annualized amounts. `convert_to_annual` scales an existing `job_data` dict in place (hourly×2080, monthly×12, weekly×52, daily×260) and sets `interval="yearly"`.
**Invariant:** salary parsing REFUSES to answer rather than guess — any out-of-window, missing max, or `min >= max` returns `(None,None,None,None)`. `enforce_annual_salary` only changes the RETURNED amounts, not the interval classification. The `k` suffix is applied per side independently.
**Probe:** no in-repo test suite (the function docstring itself notes "TODO: Needs test cases as the regex is complicated"); `currency_parser` locale handling and `extract_job_type` keyword regex are documented in source. Verified against source.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "JobSpy", query: "extract_salary currency_parser convert_to_annual", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt refuse-to-guess salary parsing (threshold interval inference, per-side `k` suffix, sanity window, `min<max` guard) and locale-safe currency parsing (integer-part-only separator stripping). Adapt thresholds/annualization factors to your currency/market. Omit the USD hardcode if you parse multiple currencies. Coverage caveat: no in-repo tests; the source docstring flags the regex as needing test coverage.
