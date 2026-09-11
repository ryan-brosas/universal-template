<!-- capsule-v2 -->
# Httpx client lifecycle — who closes the shared AsyncClient, and when does that silently fail?

**Source:** TypeChat MIT `main@83caa1242d9a9a707a4a66bfbc5fe6174cbcb8dc`; Codebase Memory `typechat`. **Question:** How do I own the async HTTP client across event-loop lifecycles without leaking connections or hanging shutdown?

## Eager client + three-way close ladder
**Path/Symbol:** `python/src/typechat/_internal/model.py:67` (eager `_async_client = httpx.AsyncClient()` in `__init__`), `:141-147` (`__aenter__`/`__aexit__`), `:149-153` (`__del__`).
**Signature:** `__aenter__(self) -> Self`; `__aexit__(...) -> bool | None` awaiting `self._async_client.aclose()`; `def __del__(self)` (sync).

### Decisive source
```py
def __del__(self):
    try:
        asyncio.get_running_loop().create_task(self._async_client.aclose())
    except Exception:
        pass
```
**Flow:** the client is constructed eagerly at model-creation time — NOT inside a context manager or running loop. Normal disposal is `async with create_language_model(...) as model:` whose `__aexit__` awaits `aclose()`. The fallback `__del__` only works when the interpreter is garbage-collecting the model WHILE an event loop is still running on this thread: `get_running_loop()` raises `RuntimeError` otherwise, and every exception is swallowed.
**Invariant:** after `asyncio.run(...)` returns, the loop is gone — a model dropped then is NEVER closed by `__del__` (you get httpx's "Unclosed AsyncClient" warning instead of silent correctness). The created task also holds only a weak reference from the loop's task set, so even the in-loop path is best-effort. Porters must treat explicit `aclose()`/context-manager use as the contract and `__del__` as a diagnostic-only net. Note `__aenter__` returns `Self` without touching the client — entering never connects; ALL connection setup stays lazy inside httpx.
**Probe:** no dedicated upstream test exercises lifecycle (`tests/test_model.py` covers size limits only, via a subclass that swaps `_async_client` for a MockTransport client at :15-17 — proving the attribute is the sanctioned injection point). Static pins executed: `grep aclose model.py` = 2 (:147 :151); `grep 'except Exception' model.py` = 2 (:107 retry, :152 swallow). EXECUTED live this pass: the four size-limit tests that DO exercise `complete()` through the swapped client pass under Python 3.14.7 (`pytest -vv` → **22 passed, 17 snapshots**); the `__aenter__/__aexit__/__del__` ladder itself remains zero-test — caveat stands.
**Retrieve:**
```ts
// CLI: codebase-memory-mcp cli search_graph '{"project":"typechat","query":"HttpxLanguageModel aexit adel aclose","limit":5}'
// rank1 __aexit__ 146-147; __del__ fetched via get_code_snippet qn ...model.HttpxLanguageModel.__del__
```

## Verdict
Adopt eager-client + explicit-close ownership and the private `_async_client` swap point for transport fakes; adapt to host HTTP stacks with real lifecycle hooks; omit `__del__` entirely rather than port it — a close that only works mid-loop invites false confidence. Coverage caveat: lifecycle paths have zero upstream tests; claims are source-pinned.
