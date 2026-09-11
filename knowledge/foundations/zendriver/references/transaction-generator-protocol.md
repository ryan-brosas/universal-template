<!-- capsule-v2 -->
# transaction-generator-protocol — how does a CDP command become an awaited, typed result without a code-generated client?

**Source:** zendriver MIT `main@2c6d9c7daaab543d34e9fe2b0ef7eaa171c79760`; Codebase Memory `ext-zendriver`. **Question:** How are protocol commands encoded, correlated by id, and resolved into typed Python objects with zero per-command glue?

## Transaction wraps a cdp generator send/recv loop
**Path/Symbol:** `zendriver/core/connection.py:Transaction` (:82-142) and `Connection.send` (:535-585).
**Signature:** `Transaction(cdp_obj: Generator[dict[str, Any], dict[str, Any], Any])`; `async def send(self, cdp_obj: Generator[...], _is_update: bool = False) -> T`.
**Data Shape:** every generated `cdp.<domain>.<method>()` returns a *generator*; `next()` yields the request dict and `send(response)` resumes it; the generator's StopIteration carries the parsed typed result. `Transaction` is itself an `asyncio.Future`.

### Decisive source
```python
# Transaction.__init__ (:92-95)
self.method, *params = next(self.__cdp_obj__).values()
if params:
    params = params.pop()
self.params = params
# Transaction.__call__ (:122-128)
try:
    # try to parse the result according to the py cdp docs.
    self.__cdp_obj__.send(response["result"])
except StopIteration as e:
    # exception value holds the parsed response
    return self.set_result(e.value)
raise ProtocolException("could not parse the cdp response:\n%s" % response)
```

**Flow:** `send()` → `aopen()` (lazy websocket) → build `Transaction`, allocate id from a fresh-per-empty-mapper `itertools.count` under `_current_id_mutex` → register in `self.mapper[id] = tx` → (unless `_is_update`) reconcile auto-enabled domains → `websocket.send(tx.message)` → listener pops `mapper[id]` on reply and calls `tx(**message)`. `"error"` in the response becomes `set_exception(ProtocolException(...))` (:119-121).
**Invariant:** the id→transaction mapper entry is popped exactly once by the listener (`pop(message["id"])`, :815 — added to fix a memory leak); a port that leaves entries in `mapper` leaks futures on every command.
**Probe:** `grep -c '__cdp_obj__.send(response' zendriver/core/connection.py` → 1 (the parse-resume site at :124); direct test: `tests/core/test_tab.py` handler tests exercise this loop through real commands.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "Connection send Transaction cdp_obj", limit: 5 });
```

## Verdict
Adopt the generator-as-command protocol and future-correlated id map verbatim (it is what makes arbitrary CDP callable with no client codegen); adapt the id allocator only if you drop the event-transaction reuse of `__count__`; omit zendriver's `CantTouchThis` metaclass guard unless you also port shared class-level state. No coverage caveat: source read whole-file and probe executed against the pin.
