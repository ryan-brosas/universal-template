<!-- capsule-v2 -->
# BrowserError memory channel + act() result-normalization funnel — how do handler errors reach the LLM as memory instead of crashing the step?

**Source:** browser-use MIT `main@3c989dc`; Codebase Memory `browser-use`. **Question:** how does a rich error thrown deep in a watchdog handler become structured short-term/long-term memory on the ActionResult the LLM sees?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/tools/service.py` — `handle_browser_error` (:193), `Tools.act` result tail (:2306-2320); raising sites across actions (`raise BrowserError(msg, long_term_memory=msg)` e.g. upload :1035).
**Signature:** `handle_browser_error(e: BrowserError) -> ActionResult`; `BrowserError(message, long_term_memory=..., short_term_memory=...)`.

### Decisive source
```python
def handle_browser_error(e: BrowserError) -> ActionResult:
    if e.long_term_memory is not None:
        if e.short_term_memory is not None:
            return ActionResult(
                extracted_content=e.short_term_memory,
                error=e.long_term_memory,
                include_extracted_content_only_once=True,
            )
        else:
            return ActionResult(error=e.long_term_memory)
    # Fallback: NEVER silently stringify a BrowserError without long_term_memory
    logger.warning('⚠️ A BrowserError was raised without long_term_memory ...')
    raise e   # re-raise so the bug is loud instead of feeding garbage to the LLM

# act() normalizes whatever a handler returned:
if isinstance(result, str): return ActionResult(extracted_content=result)
elif isinstance(result, ActionResult): return result
elif result is None: return ActionResult()
else: raise ValueError(f'Invalid action result type: {type(result)} of {result}')
```

**Flow:** handler raises `BrowserError` carrying optional `long_term_memory` (the LLM-facing explanation) and optional `short_term_memory` (once-only detail) → `act()` catches it and routes through `handle_browser_error` → both memories land on the ActionResult (`error=` field carries long-term text; extracted content marked include-only-once when short-term present) → plain `Exception`s become `ActionResult(error=str(e))`; str/None returns are wrapped.
**Invariant:** a BrowserError WITHOUT `long_term_memory` must re-raise, not degrade — stringifying it would feed the LLM an unstructured traceback; `include_extracted_content_only_once=True` prevents the short-term detail from being replayed into every later prompt.
**Probe:** `tests/ci/browser/test_element_click_error.py`, `tests/ci/test_multi_act_guards.py` (navigate terminates sequence; errors abort remaining actions :165).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "browser-use", query: "handle_browser_error BrowserError long_term_memory ActionResult", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-slot memory channel (error=long-term LLM guidance, extracted_content=once-only detail) and the loud re-raise for unannotated BrowserErrors; adapt ActionResult fields to host; omit the emoji log cosmetics.
