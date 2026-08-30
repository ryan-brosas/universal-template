<!-- capsule-v2 -->
# Exception canonicalization fingerprints — how are repeated exceptions grouped regardless of line numbers or paths?

**Source:** logfire MIT `main@e484a6b5`; Codebase Memory `ext-logfire`. **Question:** What exactly enters the fingerprint hash so that the same bug matches across deploys but different bugs don't collide?

## canonicalize_exception_traceback + record_exception wiring
**Path/Symbol:** `logfire/_internal/utils.py:canonicalize_exception_traceback` (`utils.py:470-533`) + consumption in `tracer.py:record_exception` (`tracer.py:422-486`).
**Signature:** `canonicalize_exception_traceback(exc: BaseException, seen: set[int] | None = None) -> str`; fingerprint = `sha256_string(canonical_repr)`.
**Data Shape:** canonical text built from `module.qualname\n----` + frames rendered as `module.funcname\n   SOURCE_LINE` (linecache, stripped); recursion guard caps repeats at ≥100 frames only for RecursionError.

### Decisive source
```python
frame_summary = f'{module}.{frame.f_code.co_name}\n   {source_line}'
if frame_summary in visited:
    num_repeats += 1
    if num_repeats >= 100 and isinstance(exc, RecursionError):
        parts.append('\n<recursion detected>'); break
else:
    visited.add(frame_summary); parts.append(frame_summary)
...
if isinstance(exc, BaseExceptionGroup):
    parts += ['\n<ExceptionGroup>',
              *sorted({canonicalize_exception_traceback(e, seen) for e in sub_exceptions}),
              '\n</ExceptionGroup>\n']
if exc.__cause__ is not None:      # cause and context are DIFFERENT labels
    parts += ['\n__cause__:', ...]
if exc.__context__ is not None and not exc.__suppress_context__:
    parts += ['\n__context__:', ...]
```
Docstring states the contract: "The source line is used, but not the line number… The module is used instead of the filename. The same line appearing multiple times in a stack is ignored. Exception group sub-exceptions are sorted and deduplicated."
Routing nuance in tracer.record_exception: when FastAPI instrumentation recorded the exception first (`recorded_by_logfire_fastapi` attr), the fingerprint goes into the EVENT attributes, not the span — "`_tweak_fastapi_span` will copy it to the span if the span ends up having level error… If it's handled, the same exception will be recorded on the span again by the OTel instrumentation… In that case there won't be recorded_by_logfire_fastapi." Also `traceback.format_exception` is globally patched (`tracer.py:489-500`) to never raise (returns `'Formatting stacktrace failed: …'`).
**Flow:** exception escapes or is recorded → canonical string assembled with dedupe/groups/cause-context → sha256 → stored as `logfire.exception.fingerprint` on the span (or event pending status confirmation) → backend groups issues by fingerprint.
**Invariant:** Line numbers and file PATHS must NOT enter the hash (any edit elsewhere would orphan groups); module+function+source-line identity is stable. Cause vs context distinction preserved deliberately. The `seen` id-set prevents infinite cause/context cycles.
**Probe:** `tests/test_utils.py` (canonicalization cases incl. groups/cycles) — direct runner available.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-logfire", query: "canonicalize_exception_traceback issue_fingerprint_source record_exception", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt canonical-traceback hashing wholesale for error grouping. Adapt the fingerprint attribute key and event-vs-span deferral to your pipeline. Omit the RecursionError special case at your peril — it exists because recursion tail frames vary run-to-run.
