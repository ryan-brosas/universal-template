<!-- capsule-v2 -->
# CSV cell-safety pair — how do I keep giant or hostile values from stalling or corrupting an append-only CSV ledger writer?

**Source:** Auto_job_applier_linkedIn MIT `main@0ca5550f8aa80027621cfc17a30fceba05705f84`; Codebase Memory `Auto_job_applier_linkedIn`. **Question:** job descriptions reach hundreds of KB — which two ends of the CSV pipeline must be tuned together so writes never raise and reads never truncate silently?

## Interpreter field-cap raise + never-raise writer-side truncation with marker suffix
**Path/Symbol:** `runAiBot.py:26` (`csv.field_size_limit(1000000)`, module import); `modules/helpers.py:truncate_for_csv` (:236–247); applied at every ledger write: `submitted_jobs` (:820–822) and `failed_job` (:780) map `{key: truncate_for_csv(value)}`; header-once via `file.tell() == 0` (:773, :813).
**Signature:** `truncate_for_csv(data, max_length: int = 131000, suffix: str = "...[TRUNCATED]") -> str`.
**Data Shape:** any value (None, sets, exceptions, dicts) → one safe string; oversized strings keep exactly max_length chars ending in the marker suffix.

### Decisive source
```python
csv.field_size_limit(1000000)          # import-time: let the csv MODULE accept ~1MB fields
def truncate_for_csv(data, max_length=131000, suffix="...[TRUNCATED]"):
    try:
        text = "" if data is None else str(data)            # coerce anything
        if len(text) <= max_length: return text
        return text[:max_length - len(suffix)] + suffix      # marker keeps truncation VISIBLE
    except Exception as e:
        return f"[could not stringify value: {e}]"           # the coercer itself never raises
...
writer.writerow({key: truncate_for_csv(value) for key, value in record.items()})
if csv_file.tell() == 0: writer.writeheader()                # header-once on append-mode files
```

**Flow:** import raises the interpreter cap once → every ledger row coerces each cell through truncate_for_csv → append-mode open → header written only when the file is brand-new (tell==0) → row appended. Failures to WRITE the ledger alert loudly but never kill the run.
**Invariant:** the two limits are a PAIR: writer-side max_length (131k) stays comfortably under the reader/writer field cap (1M), so a truncated cell can always round-trip back through csv.reader; and no cell can ever raise — even the coercion failure path returns a diagnostic string.
**Probe:** `tests/test_helpers.py::test_truncate_for_csv_shortens_long_values_with_suffix` (500 chars, max 50, "...CUT" → len==50, endswith marker), plus pass-through/None/coercion cases (:57–73) — executed this pass: test_helpers.py 19/19 passed; full suite 56 passed / 0 failed / 1 live-skipped.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Auto_job_applier_linkedIn", query: "truncate_for_csv submitted_jobs failed_job", limit: 6 });
// → runAiBot.failed_job :765-784 · runAiBot.submitted_jobs :802-826 · modules.helpers.truncate_for_csv
```

## Verdict
Adopt the pair semantics: set csv.field_size_limit above your writer cap at import; funnel EVERY ledger cell through one total stringifier with a visible truncation marker; header-once via tell()==0 on append handles. Adapt the two constants to your storage limits. Omit per-field custom encodings — one chokepoint is the point. Contrast: dedupe-applied-tracking owns reading this ledger's first column; ledger-contrast-csv-vs-summary owns file-level roles — this capsule owns only CELL safety.
