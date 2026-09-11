<!-- capsule-v2 -->
# Log method internals — how do logs differ from spans at creation time, and how does exc_info upgrade work?

**Source:** logfire MIT `main@e484a6b5`; Codebase Memory `ext-logfire`. **Question:** Why is a log an instantaneously-started-and-ended span, and what exactly happens for each exc_info shape?

## Logfire.log
**Path/Symbol:** `logfire/_internal/main.py:Logfire.log` (`main.py:722-839`).
**Signature:** `log(level: LevelName|int, msg_template: str, attributes=None, tags=None, exc_info: ExcInfo=False, console_log: bool|None=None) -> None`.
**Data Shape:** span_type='log' attribute; level attributes merged; DISABLE_CONSOLE_KEY set per-call; uses `_logs_tracer` (is_span_tracer=False).

### Decisive source
```python
if (msg := attributes.pop(ATTRIBUTES_MESSAGE_KEY, None)) is None:
    fstring_frame = inspect.currentframe()
    if fstring_frame.f_back.f_code.co_filename == Logfire.log.__code__.co_filename:
        # user called logfire.info etc., not logfire.log directly
        fstring_frame = fstring_frame.f_back
    msg, extra_attrs, msg_template = logfire_format_with_magic(...)
else:
    # message already filled by a logging integration; make sure it's a string
    msg = merged_attributes[ATTRIBUTES_MESSAGE_KEY] = str(msg)
    msg_template = str(msg_template)
...
start_time = self._config.advanced.ns_timestamp_generator()
span = self._logs_tracer.start_span(msg_template, attributes=otlp_attributes, start_time=start_time)
if not span.is_recording(): return
if exc_info:
    if exc_info is True: exc_info = sys.exc_info()
    if isinstance(exc_info, tuple): exc_info = exc_info[1]
    if isinstance(exc_info, BaseException):
        span.record_exception(exc_info)
        if otlp_attributes[ATTRIBUTES_LOG_LEVEL_NUM_KEY] >= LEVEL_NUMBERS['error']:
            set_exception_status(span, exc_info)   # status description = exception message
span.end(start_time)
```
Pre-filtering: `level_num < self.config.min_level` returns BEFORE any formatting cost; underscore-prefixed attribute keys raise ValueError in every convenience wrapper (trace/debug/info/notice/warning/error/fatal/exception/span).
**Flow:** min-level gate → stack-info merge → format (magic or pre-filled from logging handler) → OTLP coercion → tags/sample-rate/console-disable plumbing → start span with log attrs → optional exception event (+ERROR status only when level ≥ error: "OTEL only lets us set the description when the status code is ERROR") → end with SAME timestamp as start (zero-duration record).
**Invariant:** The frame-hop check exists because info()/error() delegate through log() — without it f-string magic would bind to the wrapper's frame. Pre-filled messages (from stdlib logging integration) bypass magic entirely but coerce both msg and template to str. `console_log=False` marks the record invisible to the console exporter while still shipping.
**Probe:** `tests/test_logs.py` / test_main log tests — pin exc_info ladder and pre-filled-message path.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-logfire", query: "Logfire.log set_exception_status DISABLE_CONSOLE_KEY ATTRIBUTES_SPAN_TYPE_KEY", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: logs-as-zero-duration-spans, min-level early gate, exc_info normalization tuple→exception→status-gated, frame-hop detection for wrapper methods. Adapt attribute names to your schema. Omit the logging-integration compat branch if you have none.
