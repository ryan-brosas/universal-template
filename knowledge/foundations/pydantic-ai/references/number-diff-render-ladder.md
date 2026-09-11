<!-- capsule-v2 -->
# Number/duration diff renderers — how do report diffs decide between '+0.7 / +70.0%' and '12.5x', and when is a difference "significant"?

**Source:** pydantic-ai MIT `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** What are the exact formatting rules for values, relative diffs, and durations — including the small-base drop rule and ASCII-only fallbacks?

## percentage/multiplier ladder + atol+rtol significance
**Path/Symbol:** `pydantic_evals/pydantic_evals/reporting/render_numbers.py` — `default_render_number` (:24-51), `default_render_number_diff` (:62-94), `_render_relative` (:132-161), `_render_duration` (:164-189); styling in `reporting/__init__.py:_NumberRenderer._get_diff_style` (:957-965) + `infer_from_config` kind defaults (:896-937).
**Signature:** `default_render_number(value) -> str` (ints comma-grouped; floats ≥1 sig-figs with ≥1 decimal; <1 via exponent); `default_render_duration(seconds)` µs/ms/s unit ladder.
**Data Shape:** config TypedDicts `RenderValueConfig`/`RenderNumberConfig` (value_formatter, diff_formatter, diff_atol=1e-6, diff_rtol int-aware 0.001 vs float 0.05, increase/decrease styles).

### Decisive source
```python
# _render_relative: percentage at-or-below 1x, multiplier above; drop on noise
if abs(base) < small_base_threshold and abs(delta) > MULTIPLIER_DROP_FACTOR * abs(base):
    return None
...
if perc_str in ('+0.0%', '-0.0%'):
    return None
if abs(delta) / abs(base) <= 1:
    return perc_str                       # '+70.0%'
multiplier = new / base
return f'{multiplier:,.1f}x' if abs(multiplier) < MULTIPLIER_ONE_DECIMAL_THRESHOLD else f'{multiplier:,.0f}x'

# _get_diff_style: significance = atol + rtol*|old|
if abs(diff) < self.diff_atol + self.diff_rtol * abs(old): return None
return self.diff_increase_style if diff > 0 else self.diff_decrease_style
```

**Flow:** value strings always shown → equal rendered strings collapse to one string → differing strings joined by arrow (`→`, or `->` under ascii_only) → if significant, name bolded, style applied, optional diff text appended. Style polarity INVERTS between kinds: score up = green/red down, metric/duration up = red/down green (durations use rtol=0.1). Sub-ms durations print µs but swap to `us` when the console can't encode it (`console_table` duration_config override :576-585).
**Invariant:** The BASE_THRESHOLD=1e-2 / MULTIPLIER_DROP_FACTOR=10 rule exists because 'from 0.001 to 5' as '+499900.0%' or '5000.0x' is noise — relative text is dropped, absolute kept. A porter who keeps the multiplier branch there produces unreadable diffs. Zero base also drops relative (division guard), and rounded-to-zero percentages are suppressed.
**Probe:** `tests/evals/test_render_numbers.py::test_default_render_number_diff` (:61+) and `test_default_render_duration_diff` pin exact strings incl. signed µs; ascii fallback pinned in `test_reporting.py` glyph tests.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-pydantic-ai","query":"default_render_number_diff","limit":3,"detail":"compact"}'
```
Live check this pass: rank-2 line-exact `render_numbers.py 62-94`.

## Verdict
Adopt the formatting ladders and significance predicate verbatim — they encode hard-won readability rules. Adapt style names to your renderer. Omit rich-specific markup only if you have no styled terminal target. Direct tests executed GREEN at pin.
