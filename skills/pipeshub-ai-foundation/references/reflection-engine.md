<!-- capsule-v2 -->
# Reflection engine — how does a failed run become an actionable, retry-shaped ErrorAnalysis instead of a raw stack trace?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** What regex ladder categorizes LLM-authored code failures so the model can self-correct on the next attempt without re-parsing stacks?

## Category → canned-suggestion mapping with one targeted override
**Path/Symbol:** `backend/python/app/agent_loop_lib/sandbox/coding/reflection.py:ReflectionEngine.analyze/_analyze_typescript/_analyze_python` (L82–180); `_missing_input_file_suggestion` (L53–64); `_suggestion_for` (L67–76).
**Signature:** `analyze(result: CodeResult) -> ErrorAnalysis | None` — stateless, pure function of the result; returns None iff `result.success`.
**Data Shape:** `ErrorAnalysis{category: syntax|type|runtime|import|timeout|permission|unknown, message, file?, line?, column?, suggestion?, stack_trace, is_retryable=True}`. TS path extracts tsc diagnostics `file(line,col): error TSxxxx:`; Node frames `at fn (path:l:c)`; Python last-line `ExcType: msg` + reversed scan for `File "f", line N`.

### Decisive source
```python
# Import-hint check runs against the FULL text FIRST, regardless of whether
# _NODE_ERROR_RE matched — Node's require()/ESM resolver throws a plain
# `Error: Cannot find module '...'` (NOT a named subclass like TypeError),
# so gating this check on node_match would miss the single most common
# import failure.
if error_type == "SyntaxError":      category = ErrorCategory.SYNTAX
elif any(hint in lowered for hint in _IMPORT_HINTS):
                                     category = ErrorCategory.IMPORT
elif error_type is not None:         category = ErrorCategory.RUNTIME
else:                                category = ErrorCategory.UNKNOWN
...
suggestion=_missing_input_file_suggestion(text) or _suggestion_for(category)
```

**Flow:** success → None → timeout shape (`exit_code == -1` + "timed out") → TIMEOUT → language dispatch → TS: tsc diagnostic (TYPE) else named/plain error + import hints + frame coords → PY: last-line exception type → category ladder + deepest frame via reversed line scan → every failure gets `is_retryable=True` and either the input-file override or its category's canned suggestion.
**Invariant:** (1) The `input/…` FileNotFoundError override reframes an "error" as NORMAL absence ("files under `input/` are only present when the calling agent explicitly staged that data — guard the read") — without it a model burns retries on expected-miss reads. (2) Import detection must run on full text, not gated on a named-error match (Node throws PLAIN Error for module resolution). (3) Deliberately best-effort regex, not a real parser — no typescript/ast dependency just for messages. (4) Composition direction: executor leaves `error_analysis=None`; the SANDBOX composes reflection in (`model_copy(update={...})`) — never double-populate.
**Probe:** `tests/unit/agent_loop_lib/sandbox/test_reflection.py::test_python_missing_parent_results_file_gets_targeted_suggestion` (:26), `::test_typescript_enoent_on_input_path_gets_targeted_suggestion` (:58), `::test_python_other_file_not_found_keeps_generic_runtime_suggestion` (:39), `::test_unrelated_python_error_is_unaffected` (:75).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "ReflectionEngine analyze ErrorCategory _missing_input_file_suggestion", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the category vocabulary + canned-suggestion map + targeted input-absence override for any execute-code tool feeding an LLM retry loop; adapt regexes to host languages. Omit PipesHub's specific hint strings tied to its own staging paths only if your staging contract differs. Direct tests pin both targeted-override branches and non-interference at HEAD.
