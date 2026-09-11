<!-- capsule-v2 -->
# Sensitive-value redaction ladder — how do you scrub secrets from strings without partial-match leaks or cascade corruption?

**Source:** browser-use MIT `main@3c989dc`; Codebase Memory `browser-use`. **Question:** how do you replace secret values in LLM-visible text when secrets may be substrings of each other or of their own placeholder syntax?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/utils.py` — `collect_sensitive_data_values` (:59), `redact_sensitive_string` (:76); key-name detection twin `_detect_sensitive_key_name` in `tools/service.py` (:176).
**Signature:** `redact_sensitive_string(value: str, sensitive_values: dict[str, str]) -> str`.

### Decisive source
```python
def redact_sensitive_string(value, sensitive_values):
    if not sensitive_values: return value
    # Build lookup from secret text -> key name, LONGEST secrets first so the
    # regex alternation prefers the longest match.
    sorted_items = sorted(sensitive_values.items(), key=lambda item: len(item[1]), reverse=True)
    secret_to_key = {secret: key for key, secret in sorted_items}
    # Single-pass replacement: each position is consumed at most once, so earlier
    # replacements cannot be corrupted by later ones.
    pattern = re.compile('|'.join(re.escape(secret) for secret in secret_to_key))
    return pattern.sub(lambda m: f'<secret>{secret_to_key[m.group(0)]}</secret>', value)
```
```python
# tools/service.py — reverse direction: which KEY was typed into a field?
def _detect_sensitive_key_name(text, sensitive_data):
    # New format {domain: {key: value}} AND legacy {key: value} both flattened;
    # returns the placeholder NAME so logs say 'Typed <password>' not the value.
```

**Flow:** domain-scoped and legacy dicts flattened to placeholder→value map → sort by secret LENGTH descending → ONE compiled alternation pass replaces every occurrence position-exclusively → output uses `<secret>key</secret>` tags. The input action separately detects which key name matches the typed text so agent memory records the placeholder, never the value.
**Invariant:** longest-first ordering is load-bearing (#5135): a shorter secret that is a substring of another (or of the word `secret` itself) must not win the alternation or corrupt earlier replacements; single-pass consumption means the replacement output can never be re-matched by the same pattern; empty dict short-circuits to identity.
**Probe:** `tests/ci/test_redact_cascade.py` — substring-secret regression (:13), overlapping-prefix pair (:25), tag-syntax secret value (:37), multi-occurrence (:44); `tests/ci/security/test_sensitive_data.py` for the input-path twin (:42+:276).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "browser-use", query: "redact_sensitive_string collect_sensitive_data_values _detect_sensitive_key_name sensitive_data", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt longest-first single-pass alternation redaction verbatim (it is host-independent); adapt the `<secret>` tag vocabulary to your prompt conventions; omit the domain-scoping layer if you have no per-domain secrets.
