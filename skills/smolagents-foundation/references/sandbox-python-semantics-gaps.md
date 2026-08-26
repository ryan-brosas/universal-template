<!-- capsule-v2 -->
# Interpreter Python-semantics gaps — which ordinary constructs behave differently inside evaluate_ast, and why?

**Source:** smolagents Apache-2.0 `main@30bb1161`; Codebase Memory `ext-smolagents`. **Question:** A porter re-implements the AST walker — where does "obvious" Python semantics diverge (boolops, comparisons, comprehensions, with-unwind, fuzzy names, print), and what breaks if each is ported naively?

## Divergence ledger
**Path/Symbol:** `src/smolagents/local_python_executor.py` — `evaluate_boolop` (:710-727), `evaluate_condition` (:962-1001), `_evaluate_comprehensions` (:1056-1096), `evaluate_name` close-matches (:941-959), `evaluate_with` exc_info unwind (:1236-1268), `evaluate_call` print special-case (:902-904), `evaluate_subscript` suggestions (:921-938), `evaluate_augassign` list guard (:665-671).
**Signature:** All evaluators share `(expression, state, static_tools, custom_tools, authorized_imports)`; state dict IS the namespace.
**Data Shape:** Result-propagation convention: statement evaluators return the last non-None line result (`evaluate_if`, `evaluate_for`) so top-level expressions still produce output.

### Decisive source
```python
# :996-1000 — chained comparisons with truthiness-object tolerance:
if current_result is False:      # identity check, not bool(): pandas Series truth-value
    return False
result = current_result if i == 0 else (result and current_result)
left = right                      # chaining carries the COMPARATOR value, not a bool
# :1085-1087 — comprehension scoping: fresh copy per iteration (Python 3 semantics)
for value in iter_value:
    new_state = state.copy()
    set_value(comprehension.target, value, new_state, ...)
```

**Flow:** BoolOps short-circuit returning the DECIDING VALUE (`a or b` yields the operand, not bool) — but only because evaluation order is manual; comparators chain left-to-right carrying values. Comprehension variables never leak (per-iteration state.copy) while loop targets DO leak into state (plain `for` sets target in the shared state). `with` implements full multi-manager unwind: exit exceptions REPLACE the active exception; suppression resets exc_info to (None,None,None) for outer managers; no-as-clause managers still exit. Unknown names trigger difflib.get_close_matches against state keys — a typo like `total_cout` RESOLVES to `total_count` (deliberate LLM-forgiveness, test-pinned). `print` writes into `state["_print_outputs"]` via str-join instead of stdout so logs survive remote execution.
**Invariant:** These are semantic CHOICES tuned for model-authored code, not bugs: fuzzy-name resolution trades determinism for agent resilience; value-returning boolops match real Python; the pandas-safe `is False` identity check exists because numpy/pandas objects raise on bool(). Porters who "fix" any of these change what generated code can express.
**Probe:** `tests/test_local_python_executor.py::test_boolops/:test_multiple_comparators/:test_evaluate_condition_with_pandas*` (:1781-2029), `test_listcomp_nested` (:540), with-suite matrix (:1030-1218), `test_close_matches_subscript` (:1381). Live: `total_count=7; result = total_cout` → 7.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-smolagents", query: "evaluate_boolop evaluate_condition get_close_matches _evaluate_comprehensions", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the ledger as a conformance checklist when reimplementing the evaluator. Adapt the fuzzy-match radius and suggestion formatting per product taste. Omit nothing from the with-unwind matrix — it is the most-tested region of the file.
