<!-- capsule-v2 -->
# ArgumentCorrectness occurrence selection — how do you assert on a specific invocation's arguments when a tool ran multiple times?

**Source:** pydantic-ai MIT `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How should an evaluator pick WHICH call of a repeatedly-invoked tool to inspect, and what graceful-failure ladder precedes argument comparison?

## first/last/index selection + five-step failure ladder
**Path/Symbol:** `pydantic_evals/pydantic_evals/evaluators/agentic.py:ArgumentCorrectness` (:384-487, `_select` :477-487); diff helper `_diff_arguments` (:490-502).
**Signature:** `occurrence: Literal['first','last'] | int` (0-based; negative ints unsupported); `_select(matches: list[_ToolCallInfo]) -> _ToolCallInfo | None`.
**Data Shape:** expected_arguments = `dict[str, Any]` compared against JSON-parsed span arguments; match_mode `'subset'` (default) or `'exact'`.

### Decisive source
```python
if self.occurrence == 'first': return matches[0]
if self.occurrence == 'last':  return matches[-1]
if not isinstance(self.occurrence, int):  # runtime guard: plain dataclasses don't validate the annotation
    return None
index = self.occurrence
if 0 <= index < len(matches): return matches[index]
return None
```

**Flow:** gather tool spans for the named tool (respecting include_failed) → no matches ⇒ fail `'No calls to tool %r were recorded.'` → selection returns None ⇒ fail with count + legal-values message → `arguments is None` ⇒ fail hinting `include_content` may be disabled → `json.loads` failure ⇒ fail with decode error → non-dict JSON ⇒ fail with repr → `_diff_arguments`: subset reports missing keys then value mismatches per key; exact ADDITIONALLY lists unexpected actual keys.
**Invariant:** The `isinstance(self.occurrence, int)` runtime guard exists because dataclasses do not validate Literal annotations — a plain string like `'second'` must degrade to the "selects nothing" failure, not raise TypeError. Subset comparison is TOP-LEVEL-KEYS only: an expected nested dict must equal the actual value in full (documented in-source). Every failure carries a distinct actionable reason — port them all or users debug blind.
**Probe:** `tests/evals/test_agentic_evaluators.py::test_failed_attempts_excluded_by_default` (:256-258) pins that default include_failed surfaces the successful attempt's args; `include_failed=True` flips occurrence 'first' onto the failed attempt (:281-286); suite covers never-called / bad-index / args-unrecorded branches.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-pydantic-ai","query":"ArgumentCorrectness","limit":3,"detail":"compact"}'
```
Live check this pass: rank-1 line-exact `agentic.py` class + evaluate method.

## Verdict
Adopt the selection ladder and failure-reason taxonomy verbatim. Adapt the JSON parsing to your host's serialization. Omit nothing — each rung is test-pinned at pin (suite GREEN).
