<!-- capsule-v2 -->
# Secret/PII redaction detectors: checksum-validated patterns, order-dependent compilation, non-re-emitting placeholders

## Source / Question
`pydantic_ai_harness/guardrails/detectors.py` — How do you build regex-based secret/PII scrubbers that neither leak (half-matched keys under a "redacted" label, placeholders that re-emit the secret) nor destroy usability (eating whole sentences, breaking shell commands)? The hard parts are pattern ORDER, semantic validators, and honest failure modes.

## Path / Symbol
`guardrails/detectors.py` — module docstring (1–52, states its own limits: "A regex finds a credential because credentials have a shape; it does not find a prompt injection"), `_NEWLINE` (65–71, matches literal `\n` two-char sequences from pasted JSON/.env lines), `DEFAULT_SECRET_PATTERNS` (73–121), `DEFAULT_PII_PATTERNS` (123–178), `_luhn` (181–186), `_iban_mod97` (188–205), `_VALIDATORS` (207–210), `_compile` (212–243), `_require_text` (246–257), `_redactor` (260–284), `secret_data`/`personal_data` (286–330), `redact_secrets`/`redact_personal_data` ready-mades (332–341), `blocked_keywords` (333–380), `for_text` (382–406), `for_tool_result_text` (408–449).

## Signature
```python
def _compile(patterns, only, extra) -> tuple[tuple[str, re.Pattern, Callable[[str], bool] | None], ...]
def _redactor(compiled, placeholder) -> TextDetector   # replace(cleaned) if changed else allow()
```

## Data Shape
Pattern entries: `(name, compiled_regex, validator|None)` applied in DECLARATION order. Placeholders `[redacted:{name}]` name what was removed. Validators: Luhn for credit_card, ISO 7064 mod-97 (base-36 digit rotation) for IBAN. Detector returns `GuardrailResult.replace(cleaned)` only when text actually changed.

## Decisive source
1. **Order is semantics** (:226–236): `iban` BEFORE `credit_card` — the card's digit groups would otherwise claim the middle of a spaced IBAN and mislabel it; therefore "`only` filters, it does not reorder" — building the dict by iterating `only` would hand ordering to the caller's argument order (:230–235). IBAN country codes come from the closed ISO 13616 registry set (89 codes, verified 2026-07-29 against SWIFT, with re-check instructions in-comment); anchoring on real country codes is what stops build ids/patent numbers reading as accounts.
2. **Validators belong to built-ins, not names** (:216–220): a custom pattern supplied UNDER a built-in name (after `only` dropped it) would be judged by a check written for different text and silently never match — so overridden names get validator=None (:240–242).
3. **Shape+checksum both required**: Luhn discards most non-card digit runs ("roughly one in ten runs of four consecutive years satisfies the checksum by chance" :160–163); mod-97 kills `RS232 serial cable adapter and reboot` (:191–195). Card pattern takes ISO 7812 lengths 13–19 with major-industry-identifier leading digit 2–6 instead of fixed 4-4-4-4 grouping (:153–159).
4. **Placeholder cannot re-emit** (:268–275): replacement is a FUNCTION because `re.sub` reads backreferences — "a placeholder containing `\g<0>` would re-emit the very text being redacted."
5. **Key-shape completeness** (:75–77): base64url alphabet includes `_`, so a class stopping at `_` "redacts half a key and leaves the rest under a label saying it is gone, which is worse than not matching at all"; openai_key declared AFTER anthropic and excludes it explicitly so labels don't depend on declaration order; private_key alternation covers unterminated bodies (the usual paste form) but requires the header newline so prose naming both markers isn't swallowed.
6. **Refusal vs redaction defaults** (:292–296, :313–317): secrets redact (an agent quoting a key back has done the work; blocking loses it while leaving the key in history either way); emails redact (usually information the user needs delivered); blocked_keywords BLOCKS, with `(?<!\w)/(?!\w)` instead of `\b` so `C++` isn't silently inert (:365–370).
7. **Non-text boundary honesty**: `for_text`/`for_tool_result_text` refuse to guess on structured output ("substituting a scrubbed string would change the type") — 'raise' or explicit 'allow'; ToolReturn rebuilds preserving content/metadata/kind; email caveat documented: input-side PII rewrite can break `git@github.com:` commands (:31–50).

## Flow / Invariant
Compile once (order-preserving selection + extra clash refusal — extra may not silently replace a built-in) → scan text pattern-by-pattern → validator gates each match → substitute or keep → replace-verdict iff changed. Invariants: application order is part of the contract; a match without a valid checksum survives; no placeholder can resurrect the secret; detectors are plain functions (compose as chains next to custom guards).

## Probe (direct test)
`tests/guardrails/test_detectors.py`: `test_a_key_is_replaced_and_named` (:61), `test_a_private_key_is_removed_whole` (:100)/`test_an_unterminated_private_key_takes_its_body_and_stops` (:107), `test_prose_naming_both_markers_is_not_a_key` (:152), `test_scanning_a_large_paste_is_linear` (:201), `test_a_placeholder_cannot_re_emit_the_secret` (:213), `test_a_custom_pattern_is_not_judged_by_a_built_in_validator` (:219), `test_extra_may_not_silently_replace_a_built_in` (:225), `test_only_keeps_the_declared_order` (:266), `test_luhn_discards_a_digit_run_that_is_not_a_card` (:309), `test_an_identifier_is_not_an_account_number` (:331), `test_a_country_code_with_a_wrong_check_digit_is_left_alone` (:366).

## Retrieve
`search_graph --project pydantic-ai-harness --semantic-query '["secret redaction detector luhn iban"]'`

## Verdict
**Adopt** the compile-time discipline (ordered, validated, clash-checked patterns) and the function-placeholder rule for any scrubber. **Adopt** redaction-vs-refusal default reasoning per data class. **Adapt** the pattern set to your threat model; keep the registry-verification comment convention for external assumptions.
