<!-- capsule-v2 -->
# Phone-field selector ladder — how do you fill a known-value field when the form markup is generated and unknown until runtime?

**Source:** EasyApplyJobsBot CC BY-NC-SA 4.0 (learn-only: patterns + control flow, zero verbatim reuse) `main@70fe7484ebe78646fc8e2dd2612459f37eed7a9f`; Codebase Memory `EasyApplyJobsBot`. **Question:** which ordered attempts fill a phone number across arbitrary generated widgets WITHOUT overwriting anything the user already answered?

## Config→YAML value ladder + CSS-then-translate-XPath families gated visible-and-empty
**Path/Symbol:** `linkedin.py:Linkedin.fillPhoneNumber` (:368–463).
**Signature:** `fillPhoneNumber(self) -> None`.
**Data Shape:** value from `config.Phone` attr else `additionalQuestions.yaml` → `inputField['Phone Number']`; 7 CSS selector families; 4 `translate()` case-insensitive XPath families.

### Decisive source
```python
if hasattr(config, 'Phone') and config.Phone and config.Phone.strip():
    phone_number = config.Phone.strip()
else:
    ... questions['inputField'].get('Phone Number', '').strip()
if not phone_number:
    return  # No phone number configured, skip filling
...
if phone_input.is_displayed():
    current_value = phone_input.get_attribute("value") or ""
    if current_value == "":
        phone_input.clear(); phone_input.send_keys(phone_number)
```

**Flow:** resolve the value (config attr → YAML file, both stripped) → no value ⇒ silent early return → CSS families in order (type=tel / name* / id* / aria-label* / placeholder* / data-test-single-line-text-input / class*) → XPath `translate(@attr,…)` families → per candidate input: visible AND empty gate → clear+send_keys+0.5s → `phone_filled` latch breaks inner and outer loops → whole body wrapped fail-soft.
**Invariant:** NEVER overwrites a non-empty value (the empty-gate precedes every write); visible-only candidates; CSS before XPath; total failure is SILENT by design — the helper is called optimistically before Continue and before Review at multiple sites and must never become the reason a walk dies.
**Probe:** `grep -c "translate(@" linkedin.py` ⇒ 4; `grep -n "is_display()" …` ⇒ gates at :420/:444 (one per tier); `input[type='tel']` first family at :394.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "EasyApplyJobsBot", query: "fillPhoneNumber phone number input", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "EasyApplyJobsBot", qualified_name: "EasyApplyJobsBot.linkedin.Linkedin.fillPhoneNumber" });
```

## Verdict
Adopt: value ladder + ordered selector families + visible-and-empty write gate + fail-soft silence. Adapt: family lists to host widgets; add ONE loud diagnostic when a value exists but no field ever matched (upstream cannot distinguish "nothing to fill" from "field missed"). Omit: nothing structural. Cross-ref: `form-question-answering` answers unknown questions; this fills KNOWN values. Coverage caveat: no tests; grep pins + graph parity.
