<!-- capsule-v2 -->
# Redacted-persistence group sanitizer — how do you rethrow a failed session write without leaking provider payloads through an ExceptionGroup?

**Source:** OpenAI Agents Python MIT `main@cb8a2e7e`; Codebase Memory project `openai-agents-python`. **Question:** When persisting a turn fails while handling a redacted (payload-stripped) guardrail error, how is the persistence error itself made safe to cross a public boundary?

## Group-aware redaction rebuild
**Path/Symbol:** `src/agents/run_internal/run_loop.py:` `_safe_redacted_persistence_leaf_error` (:636–653), `_RedactedBaseExceptionGroup` (:656–658), `_safe_redacted_persistence_error` (:660–725); consumed at :570–589 and :762–766.
**Signature:** `def _safe_redacted_persistence_error(error: BaseException) -> BaseException`.
**Data Shape:** input arbitrary `BaseException` possibly an (possibly nested) `ExceptionGroup`; output structurally identical group of payload-free leaves; control-flow exceptions (`CancelledError`, `GeneratorExit`, `KeyboardInterrupt`, `SystemExit`) preserved as their own type.

### Decisive source
```python
if isinstance(error, asyncio.CancelledError):
    safe_error.args = (_DATA_REDACTED_ERROR_MESSAGE,)
    _mark_error_data_redacted(safe_error)
    return safe_error
...
# Snapshot the full group topology before clearing any source exception. On Python 3.10,
# the exceptiongroup backport stores children in the instance dictionary, so sanitizing a
# linked leaf can otherwise erase a group that has not been converted yet.
for current_id, current in leaf_errors.items():
    safe_errors[current_id] = _safe_redacted_persistence_leaf_error(current)
_prepare_data_redacted_error(error)
```
Leaf policy: CancelledError → same type, args replaced with the redacted message, marked; GeneratorExit/KeyboardInterrupt/SystemExit → passed through untouched; `Exception` subclasses → `UserError(_DATA_REDACTED_ERROR_MESSAGE)`; other BaseExceptions → bare `BaseException()`. Groups are rebuilt post-order so `Exception`-ness per node is preserved (`_RedactedBaseExceptionGroup` for non-Exception groups). Conversion failure fails CLOSED: source prepared + leaf-sanitized conversion error returned.

**Flow:** classify leaf vs group → snapshot topology by id → sanitize every leaf FIRST → clear provider-owned source graph once → rebuild groups bottom-up → return replacement root. The caller then `raise redacted_persistence_error from None` to suppress context chaining.

**Invariant:** Source exception objects must never cross the public boundary even as `__context__`; sanitizing leaves before clearing sources avoids the 3.10-backport mutation hazard; cancellation must stay distinguishable from ordinary failures after redaction.

**Probe:** `tests/test_error_logging_redaction.py` — pins the redaction marking/ladder behavior this helper composes with.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "safe redacted persistence exception group rebuild", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt whenever errors from one trust domain (provider SDK payloads) can be wrapped into groups crossing to another (user-facing API); adapt leaf-type mapping to your exception taxonomy; omit the 3.10 backport comment's mechanics if you target ≥3.11 natively but keep snapshot-before-mutate ordering.
