<!-- capsule-v2 -->
# Level-number scale & min_level gating — how do logfire levels map to OTEL severity, and where is the floor enforced?

**Source:** logfire MIT `main@e484a6b5`; Codebase Memory `ext-logfire`. **Question:** What are the numeric levels, how do stdlib levels translate, and why can set_level after creation bypass the gate?

## LEVEL_NUMBERS + LOGGING_TO_OTEL_LEVEL_NUMBERS + ProxyLogger.emit
**Path/Symbol:** `logfire/_internal/constants.py:LEVEL_NUMBERS` (`constants.py:14-24`, mapping table :28-80) + gates in `main.py:_span/log` (`main.py:226-227`, `754-756`) + `logs.py:ProxyLogger.emit` (`logs.py:102-122`).
**Signature:** `log_level_attributes(level: LevelName|int) -> {'logfire.level_num': int}`; invalid names warn then coerce to 'error'.
**Data Shape:** trace=1, debug=5, info=9, notice=10, warn/warning=13, error=17, fatal=21; stdlib 0→9 ("NOTSET defaults to info"), 25→11 reserved for loguru 'success'; comment: "Based on feeling rather than hard maths."

### Decisive source
```python
if level_num < self.config.min_level:
    return NoopSpan()          # _span — pre-creation gate, zero cost below floor
...
if record.severity_number is not None:
    if record.severity_number.value < self.min_level: return
elif record.severity_text and (level_name := record.severity_text.lower()) in LEVEL_NUMBERS:
    level_number = LEVEL_NUMBERS[level_name]
    if level_number < self.min_level: return
    record.severity_number = SeverityNumber(level_number)   # derive number from text
```
Docstring contract of configure(min_level): "For spans, this only applies when `_level` is explicitly specified… Changing the level of a span _after_ it is created will be ignored by this. If a span is not created, this has no effect on the current active span, or on logs/spans created inside." Provider-level push: `ProxyLoggerProvider.set_min_level` updates every live ProxyLogger (mirroring the proxy-swap protocol); `_logger_provider.set_min_level(self.min_level)` called during initialize.
**Flow:** user calls logfire.debug under min_level='info' → level_num 5 < 9 → NoopSpan returned before formatting/scrubbing spend → console exporter additionally honors per-record DISABLE_CONSOLE_KEY orthogonal to level. Stdlib handler path translates Python's 0-50 table onto the sparse OTEL scale preserving band boundaries (NOTSET→info default documented inline).
**Invariant:** The gate is CREATE-TIME ONLY by design — `span.set_level()` post-creation mutates attributes but cannot retroactively uncreate; porters must not move the gate to export time or cost-profiles change. Text→number derivation happens exactly when severity_number is missing, then MUTATES the record so downstream sees consistent fields.
**Probe:** `tests/test_logs.py::test_min_level` family — pins both gates and text derivation.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-logfire", query: "LEVEL_NUMBERS log_level_attributes min_level set_min_level", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the sparse OTEL-aligned scale plus create-time gating semantics verbatim. Adapt stdlib translation bands to your logging ecosystem. Omit loguru's success band if irrelevant.
