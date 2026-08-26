<!-- capsule-v2 -->
# Log-forging sanitizer (API side) — how are externally-sourced strings made safe before log interpolation?

**Source:** openreplay AGPL-3.0 (api MIT portions) `main@99eb600`; Codebase Memory `openreplay`. **Question:** What normalization must precede logging of request bodies, headers, URLs, or JWT claims?

## CRLF strip → control-char strip → truncate with marker
**Path/Symbol:** `api/chalicelib/utils/log.py` — `_NEWLINE_RE`, `_CONTROL_CHARS_RE`, `sanitize(value, max_length=512)` (:1–22); consumer example `issue_tracking/base_issue.py::proxy_issues_handler` (:13–17).
**Signature:** `sanitize(value, max_length: int = 512) -> str`; non-string input via `repr()`.
**Data Shape:** removes `\r\n` (log forging), null bytes + ANSI/C1 controls (`\x00-\x08\x0b-\x1f\x7f` — note `\t\n\v\f\r` gaps preserved except LF/CR), truncates to 512 appending literal `...(truncated)`.

### Decisive source
```python
def sanitize(value, max_length: int = _DEFAULT_MAX_LEN) -> str:
    """Sanitize a value before interpolating it into a log message.

    Strips CR/LF (prevents log forging), null bytes and ANSI/control
    characters, then truncates."""
    if value is None: return ""
    s = value if isinstance(value, str) else repr(value)
    s = _NEWLINE_RE.sub(" ", s)
    s = _CONTROL_CHARS_RE.sub("", s)
    if len(s) > max_length:
        s = s[:max_length] + "...(truncated)"
    return s
```

**Flow:** call at every boundary where attacker-influenced data meets a log line (the issue-tracking proxy error handler is the canonical use). Tab and other whitespace survive; only line breaks and control bytes are neutralized.
**Invariant:** Truncation marker must be appended AFTER slicing so the output never exceeds budget by more than the marker length; `None` maps to empty string, not `"None"`.
**Probe:** `grep -c 'log forging' api/chalicelib/utils/log.py` → `1`; `grep -c '...(truncated)' api/chalicelib/utils/log.py` → `1`. Direct tests: none upstream for this helper (grep-pinned caveat).
**Coverage:** clean.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openreplay", query: "sanitize log forging control chars chalicelib utils", limit: 10 });
```

## Verdict
Adopt order-of-operations (newline→control→truncate). Adapt max length. Omit repr fallback for typed-internal callers.
