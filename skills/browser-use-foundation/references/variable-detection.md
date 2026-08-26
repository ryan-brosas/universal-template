<!-- capsule-v2 -->
# Variable detection from agent history — how do you infer reusable form-field variables from what an agent did?

**Source:** browser-use MIT `main@3c989dc`; Codebase Memory `browser-use`. **Question:** how does browser-use turn past typed values into named variables using element context before falling back to value patterns?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/agent/variable_detector.py` whole (276L) — `detect_variables_in_history` (:9), `_detect_in_action` (:49), `_detect_variable_type` (:98), `_detect_from_attributes` (:123), `_detect_from_value_pattern` (:213), `_ensure_unique_name` (:259).
**Signature:** `detect_variables_in_history(history: AgentHistoryList) -> dict[str, DetectedVariable]`; `_detect_variable_type(value: str, element: DOMInteractedElement | None = None) -> tuple[str, str | None] | None`.

### Decisive source
```python
# STRATEGY ORDER IS SEMANTICS:
if element and element.attributes:
    attr_detection = _detect_from_attributes(element.attributes)
    if attr_detection: return attr_detection      # 1. element attributes WIN
return _detect_from_value_pattern(value)          # 2. value patterns only as fallback

# Attribute ladder: input type=email/tel/date/number/url first (HTML5 truth),
# then combined id+name+placeholder+aria-label keyword scan with SPECIFIC-BEFORE-GENERAL:
if 'first' in t and 'name' in t: return ('first_name', None)
elif 'last' in t and 'name' in t: return ('last_name', None)
...
# Value fallback ladder (most specific first): email regex -> phone (digit/sep, >=10 digits)
# -> YYYY-MM-DD date -> capitalized name (1 word=first, 2=full, else name; 2-30 alpha)
# -> pure digits 1-9 chars = number

def _ensure_unique_name(base_name, existing):
    counter = 2
    while f'{base_name}_{counter}' in existing: counter += 1
    return f'{base_name}_{counter}'
```

**Flow:** walk history steps → for each action dump (pydantic/dict/vars triple support) inspect only `text` and `query` fields → skip already-seen values (dedupe by VALUE set) → classify via element-context-first ladder → mint unique names with `_2` suffixes → DetectedVariable(name, original_value, type='string', format).
**Invariant:** attribute evidence must outrank value patterns or `<input type="email">` holding "5" misclassifies; value dedupe prevents one string minting multiple variables; the keyword ladder's ordering (specific names before generic 'name', address subtypes before address) is the classification contract — reordering silently changes outputs.
**Probe:** `tests/ci/test_variable_detection.py` — attribute vs pattern pairs for email (:45/:56), phone (:66/:77), date (:87/:98), first-name (:108/:119), full-name (:129), address-from-attributes (:139).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "browser-use", query: "detect_variables_in_history _detect_from_attributes _detect_from_value_pattern DetectedVariable", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-strategy classifier with its exact priority order and unique-name suffixing; adapt the field vocabulary (fields_to_check, keyword lists) to your action schema; omit history walking if you detect at input time instead.
