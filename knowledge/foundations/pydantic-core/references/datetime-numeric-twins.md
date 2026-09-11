<!-- capsule-v2 -->
# datetime numeric twins — how do int/float timestamps become datetimes vs times-of-day, and where does `val_temporal_unit` apply?

**Source:** pydantic-core MIT `main@383eb95a19433754c0cecf7025b50c26b6d97a36`; Codebase Memory `pydantic-core`. **Question:** A porter unifying numeric temporal coercion across backends must know which functions take the unit-mode config, which don't, and the deliberate overflow trick in the time path.

## Datetime honors TemporalUnitMode (seconds/milliseconds/infer); time-of-day does NOT — it is always seconds-of-day with a u32::MAX clamp that defers to speedate's >86400 error
**Path/Symbol:** `src/input/datetime.rs:int_as_datetime` (:482-508), `float_as_datetime` (:524-549), `int_as_time` (:569-606), `float_as_time` (:608-613); backend gating `src/input/input_json.rs:validate_time/validate_datetime` (:308-348).
**Signature:** `pub fn int_as_time<'py>(input, timestamp: i64, timestamp_microseconds: u32) -> ValResult<EitherTime<'py>>` (NO mode param — compare `int_as_datetime(…, mode: TemporalUnitMode)`).
**Data Shape:** speedate `DateTimeConfig/TimeConfig { unix_timestamp_offset: Some(0), .. }`; `TemporalUnitMode::{Seconds,Milliseconds,Infer}` → speedate `TimestampUnit` (validators/config.rs:26-72), config key `val_temporal_unit`.

### Decisive source
```rust
// int_as_time — negative is a hard error; huge values CLAMP so speedate raises its own error
t if t < 0_i64 => return Err(ValError::new(ErrorType::TimeParsing {
    error: Cow::Borrowed("time in seconds should be positive"), ... })),
t if t > MAX_U32 => u32::MAX, // continue and use the speedate error for >86400
...
// float_as_time — fractional part becomes microseconds, then delegate
let microseconds = timestamp.fract().abs() * 1_000_000.0;
int_as_time(input, timestamp.floor() as i64, microseconds.round() as u32)
```

**Flow:** both float entries run `nan_check!` FIRST ("NaN values not permitted" surfaced as DatetimeParsing/TimeParsing). Backend gating differs by kind and strictness: JSON Int/Float branches are gated `if !strict` and labeled `ValidationMatch::lax` while string branches stay strict-labeled (input_json.rs:314-347); BigInt time inputs get an explicit TimeTooLarge error instead of attempting conversion (:319-329); StringMapping accepts only strings. Unit mode reaches ONLY datetime/date paths (`bytes_as_datetime(..., mode)`, `int_as_datetime(..., mode)`); time/timedelta ignore it.
**Invariant:** infer semantics = large numbers are ms, small are s (speedate's threshold, pinned by tests); time-of-day is unit-INDEPENDENT forever. The clamp-to-u32::MAX is load-bearing: it converts an i64-overflow crash into speedate's "time should be ≤ 86 399" domain error — a port that range-checks eagerly must reproduce that exact error text path.
**Probe:** direct probe Q8 executed live @ pin byte-matching tests/validators/test_datetime.py::test_val_temporal_unit_datetime rows (:524-562): datetime_schema + config val_temporal_unit='infer' maps 1654646400 → 2022-06-08 but 1654646400123 → 2022-06-08T…123000; 'milliseconds' maps 1654646400 → 1970-01-20T03:37:26.400000; STRING '1654646400' also honors 'seconds' (str→bytes_as_date-time path shares the mode). Probe Q8b: time_schema rejects -1 with 'time in seconds should be positive'.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-core", query: "int float as datetime time speedate timestamp infer", limit: 10 });
// live run this pass: all four twins rank top (datetime.rs :482-613) with shared.rs str/int parsers behind them; test_val_temporal_unit_datetime surfaces as the direct-test anchor
```

## Verdict
Adopt the twin split (unit-moded datetime vs fixed seconds-of-day time) and the clamp-then-delegate error strategy verbatim; adapt speedate's parse errors into your host's message format while keeping nan/negative/overflow as DISTINCT error types; omit millisecond support for time-of-day even if your host's time type could express it — upstream deliberately doesn't. Coverage: datetime.rs, input_json.rs, validators/config.rs, tests/validators/test_datetime.py no_recorded_issue @ gen 2026-08-25T20:09:30Z.
