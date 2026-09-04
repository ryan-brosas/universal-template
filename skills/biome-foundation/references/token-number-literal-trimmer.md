<!-- capsule-v2 -->
# Number-literal trimming state machine — how do you normalize numeric literals without regexes or reparsing?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** every prettier-family formatter must trim redundant zeros/plus signs from number tokens while keeping the output byte-identical when nothing changes — what is the single-pass kernel and its lazy-allocation contract?

## The three-state byte scanner
**Path/Symbol:** `crates/biome_formatter/src/token/number.rs` — `format_trimmed_number` (:40-221), `NumberFormatOptions { keep_one_trailing_decimal_zero }` (:6-21), `FormatNumberLiteralState { IntegerPart, DecimalPart(dot_index, last_non_zero_index), Exponent(e_index, is_negative, first_digit_index, first_non_zero_index) }` (:23-38).
**Signature:** `pub fn format_trimmed_number(text: &str, options: NumberFormatOptions) -> Cow<'_, str>`.
**Data Shape:** input = the trimmed text of ONE number token (may carry sign, dot-leading form `.2`, exponent). Output = `Cow::Borrowed(input)` when no rule fires; `Cow::Owned(cleaned)` only once the first reformatting need was detected. Per-language behavior diverges through one option bit: JS prints `x.00000` as `x.0` (`keep_one_trailing_decimal_zero`), CSS prints it as `x`.

### Decisive source
```rust
// number.rs:43-50 — lowercase once via Cow, defer allocation until a rule fires:
let text = text.to_ascii_lowercase_cow();
let mut copied_or_ignored_chars = 0usize;
let mut iter = text.bytes().enumerate();
let mut curr = iter.next();
let mut state = IntegerPart;
// Will be filled only if and when the first place that needs reformatting is detected.
let mut cleaned_text = String::new();

// :209 — the hex bailout terminates the scan on ANY 'x' (0xe0 digits are not base-10):
None | Some((_, b'x') /* hex bailout */) => break,
```
**Flow:** (1) strip sign, prepend `0` if the literal starts `.` (:53-60). (2) Scan bytes; on seeing `.` enter DecimalPart tracking `dot_index` + `last_non_zero_index`; on `e` enter Exponent tracking first-digit / first-non-zero indexes. (3) At decimal/exponent TERMINATION (next char is `e` or EOF) apply the rewrite rules: all-zero fraction → drop it entirely, or keep `.0` under `keep_one_trailing_decimal_zero` only if at least one digit followed the dot (`curr_index > dot_index + 1`, :79); trailing zeros → copy up to `last_non_zero_index` (:93-97); zero-only exponent → drop from `e_index` (:99-109); exponent with leading `+`/zeros → re-emit `e`, restore `-` if negative, copy from first non-zero (:110-128). (4) `cleaned_text.is_empty()` ⇒ return the borrowed original untouched (:214-220).
**Invariant:** the lazy-Cow contract — a literal needing no change must come back `Cow::Borrowed` (test `keeps_the_input_string_if_no_change_needed` asserts exactly this), so callers can skip re-printing bookkeeping. The `unsafe NonZeroUsize::new_unchecked` calls are sound ONLY because those arms run after a digit byte was consumed (index > 0); a porter replacing indexes with unchecked non-zero wrappers must preserve that ordering. The hex bailout is load-bearing: without it `0x10e0` would be mangled by the exponent rules.
**Probe:** `crates/biome_formatter/src/token/number.rs` unit tests :231-330 pin every arm: `removes_unnecessary_plus_and_zeros_from_scientific_notation` (`1e02`→`1e2`, `1e+2`→`1e2`), `removes_unnecessary_scientific_notation` (`1e0`→`1`, `1e-0`→`1`), `does_not_get_bamboozled_by_hex` (`0xe0` unchanged, `0x10e0` unchanged), `makes_sure_numbers_always_start_with_a_digit` (`.2`→`0.2`), `keeps_one_trailing_decimal_zero` (`0.00`→`0.0` under the option), `removes_trailing_dot` (`1.`→`1`), `cleans_all_at_once` (`.00e-0`→`0.0`). Grep probes: `grep -nF 'b''x'') /* hex bailout */' crates/biome_formatter/src/token/number.rs` → 1 hit :209; `grep -c 'NonZeroUsize::new_unchecked' …` → 4.
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"biome","name_pattern":"format_trimmed_number"}'
# biome.crates.biome_formatter.src.token.number format_trimmed_number Function 40-221
```

## Verdict
Adopt the state machine + lazy-Cow contract verbatim for any literal-normalization pass over token text; adapt `keep_one_trailing_decimal_zero` to your language's trailing-zero convention; omit the `unsafe` micro-optimization if your host cannot guarantee the digit-consumed precondition. Coverage: file indexed clean (`no_recorded_issue`/`metadata_match` @ generation 2026-08-16T00:20:04Z).
