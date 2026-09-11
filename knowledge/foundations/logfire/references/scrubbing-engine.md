<!-- capsule-v2 -->
# Scrubbing engine — how are sensitive values redacted across attributes, messages, events, links, and embedded JSON without corrupting structure?

**Source:** logfire MIT `main@e484a6b5`; Codebase Memory `ext-logfire`. **Question:** What are the exact match rules (whole-value exemption, key vs value matching, JSON recursion), and what bookkeeping makes redaction auditable?

## Scrubber / SpanScrubber / MessageValueCleaner
**Path/Symbol:** `logfire/_internal/scrubbing.py:Scrubber.scrub_value` chain (`scrubbing.py:208-353`) + DEFAULT_PATTERNS (`scrubbing.py:38-70`) + SAFE_KEYS (`scrubbing.py:120-182`).
**Signature:** `scrub(path: JsonPath, value: Any) -> Any`; `_redact(match: ScrubMatch) -> Any`; patterns compiled `re.compile('|'.join([_DEFAULT_PATTERN, *extra]), re.IGNORECASE | re.DOTALL)`.
**Data Shape:** `JsonPath = tuple[str|int, ...]` (e.g. `('attributes', 'password')`, `('otel_events', 0, 'attributes')`); audit trail `list[ScrubbedNote{path, matched_substring}]` JSON-dumped into `logfire.scrubbed`.

### Decisive source
```python
DEFAULT_PATTERNS = ['password','passwd','mysql_pwd','secret',
    r'auth(?!ors?\b)',            # negative lookahead: matches auth NOT authors
    'credential','private[._ -]?key','api[._ -]?key','session','cookie',
    'social[._ -]?security','credit[._ -]?card','logfire[._ -]?token', r'pylf_v\d+_',
    *[rf'(?:\b|_){ac}(?:\b|_)' for ac in ['csrf','xsrf','jwt','ssn']]]
_DEFAULT_PATTERN_START_CHARS = 'pmsacljx_'   # cheap first-char class before trying alternatives

def scrub(self, path, value):
    if isinstance(value, str):
        if match := self._pattern.search(value):
            if match.span() == (0, len(value)):
                return value                     # WHOLE-string match = safe label like 'password'
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                return self._redact(ScrubMatch(path, value, match))
            else:
                return json.dumps(self.scrub(path, value))   # recurse into parsed JSON
    elif isinstance(value, Sequence): ...
    elif isinstance(value, Mapping):
        for k, v in ...:
            if k in BaseScrubber.SAFE_KEYS: result[k] = v          # exempt, no recursion needed for safety
            elif match := self._pattern.search(k): result[k] = self._redact(...)   # KEY match
            else: result[k] = self.scrub(path + (k,), v)           # VALUE recursion
```
Redaction default: `f'[Scrubbed due to {matched_substring!r}]'` unless a user callback returns non-None. Scope-name carve-out: spans from scopes `['logfire.openai','logfire.anthropic']` skip scrubbing entirely (LLM payloads already curated).
**Flow:** MainSpanProcessorWrapper calls `scrubber.scrub_span(span_dict)` LAST in the normalization chain (after all tweaks — order matters so tweaked messages get scrubbed too) → attributes/events/links each scrubbed with their own path prefix → BoundedAttributes wraps results because "the callback might return a value that isn't of the type required by OTEL". For message VALUES, MessageValueCleaner scrubs before truncating and appends notes into `logfire.scrubbed` alongside attribute notes.
**Invariant:** Whole-match exemption prevents absurd redaction of enum-ish labels; key-matching takes precedence over descending (a matched key redacts the whole subtree in one step); SAFE_KEYS short-circuit is also a performance guard. The compiled alternation's start-char class is load-bearing for large strings.
**Probe:** `tests/test_scrubbing.py` — pins pattern table, whole-value rule, JSON recursion, callback override.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-logfire", query: "Scrubber SpanScrubber ScrubMatch SAFE_KEYS _redact", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: pattern table shape, lookahead/authors nuance, whole-match exemption, key-first mapping walk, JSON re-parse recursion, path-addressed audit notes. Adapt the pattern list and SAFE_KEYS to your schema. Omit the OTEL BoundedAttributes wrapper if your container validates types differently.
