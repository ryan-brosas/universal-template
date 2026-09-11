<!-- capsule-v2 -->
# Structured-output coercion ladder — how do you survive JSON-schema fields that come back as strings instead of structures?

**Source:** pipeshub-ai Apache-2.0 `main@c28d133…`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** When `complete_structured()` returns nested `array`/`object` fields JSON-encoded as STRINGS, how do callers walk the result without an AttributeError deep in app code?

## Parse-and-degrade helpers between the transport and every nested walk
**Path/Symbol:** `backend/python/app/agent_loop_lib/core/structured_output.py:coerce_list/coerce_dict/coerce_optional_str` (:26 / :41 / :57).
**Signature:** `coerce_list(value: Any) -> list[Any]`; `coerce_dict(value: Any) -> dict[str, Any] | None`; `coerce_optional_str(value: Any) -> str | None`.
**Data Shape:** In: any value from a parsed `StructuredResponse.data` tree. Out: real list / dict-or-None / str-or-None. Premise: `output_schema` is a strong HINT, not a validated guarantee — providers force it via a tool-use trick (see AnthropicTransport.complete_structured), not a validator; deeper/rarer shapes drift into JSON-encoded-string form most often.

### Decisive source
```python
def coerce_list(value):                       # list passes; str is json.loads'd
    if isinstance(value, list): return value
    if isinstance(value, str):
        try: parsed = json.loads(value)
        except (json.JSONDecodeError, TypeError): return []
        return parsed if isinstance(parsed, list) else []
    return []                                 # anything else → empty, never raise

def coerce_dict(value):
    ...
        return parsed if isinstance(parsed, dict) else None   # None ≠ {}
```

**Flow:** Caller receives `response.data` → coerces EVERY nested field through the ladder BEFORE `.get()` walks → malformed entry degrades to skip/empty instead of raising. `coerce_list` failures become `[]`; `coerce_dict` failures become `None` so callers distinguish "empty object" from "not an object" and SKIP the entry rather than treat it as present-but-empty; `coerce_optional_str` stringifies non-str values because a Pydantic `str | None` field would reject e.g. an int outright.
**Invariant:** (1) Coercion happens at the WALK SITE, not in the transport — the transport returns raw data untouched so honest schema-conformant providers pay zero penalty. (2) `coerce_dict` must return None, not `{}`, on failure — collapsing that distinction silently fabricates present-but-empty objects. (3) Parsed-but-wrong-shape (`json.loads("5")`) also degrades; parse success alone doesn't validate shape.
**Probe:** No dedicated unit suite for these helpers at this pin — deterministic self-check: `python3 -c "import json;f=lambda v:(v if isinstance(v,list) else (json.loads(v) if isinstance(v,str) else []) )"` style asserts, plus the consumers' degrade paths exercised through `tests/unit/agent_loop_lib/agent/test_plan_critique_execute_loop.py` (critic issue lists ride coerce_list-style walks).
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-pipeshub-ai","query":"coerce_list coerce_dict complete_structured defensive","detail":"ids","limit":5}'
```

## Verdict
Adopt walk-site coercion with the list→[] / dict→None / stringify-or-None ladder exactly — the None-vs-empty distinction is the part porters break first. Adapt exception breadth to your JSON lib. Omit nothing. Coverage caveat stated honestly: helpers are ununit-tested at this commit; rely on consumer suites plus your own probe.
