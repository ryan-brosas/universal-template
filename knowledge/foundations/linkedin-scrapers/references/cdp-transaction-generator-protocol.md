<!-- capsule-v2 -->
# CDP transaction generator protocol — how does a cdp.<domain>.<method>() call become a wire message whose response becomes a typed result?

**Source:** zendriver AGPL-3.0 — PATTERNS ONLY, never copy verbatim. `main@2c6d9c7d`; Codebase Memory project `ext-zendriver`. **Question:** how do you turn CDP command generators into request/response futures over one websocket, and what generator shape MUST an adapter preserve?

## Generator-in, future-out
**Path/Symbol:** `zendriver/core/connection.py:ProtocolException` (:47-76), `SettingClassVarNotAllowedException` (:78), `Transaction(asyncio.Future)` (:82-143), `EventTransaction(Transaction)` (:145-168).
**Signature:** `Transaction(cdp_obj: Generator[dict, dict, T])`; properties `.method`, `.params` (extracted by ONE `next()` at construction), `.message` → `json.dumps({"method", "params", "id"})`, `.has_exception`; completion via `__call__(self, **response)` — KEYWORD-ONLY, the listener invokes `tx(**message)`.
**Data Shape:** every `cdp.*` method factory returns a **single-yield generator**: first yield = `{"method": ..., "params": ...}` dict; the caller later `.send(response_dict)` into that same yield and the generator RETURNS the parsed result (surfaced as `StopIteration.value`). `tx.id` is stamped later by `Connection.send` under `_current_id_mutex` (default `itertools.count(0)`, reset whenever `mapper` empties). `EventTransaction.__init__(event_object)` wraps `super().__init__(None)` in try/except, then `set_result(event_object)` immediately — `.event == .value == .result()`.

### Decisive source
```python
# Transaction.__init__ (:83-95)
self.method, *params = next(self.__cdp_obj__).values()
if params:
    params = params.pop()
self.params = params

# Transaction.__call__ (:110-128)
if "error" in response:
    return self.set_exception(ProtocolException(response["error"]))
try:
    self.__cdp_obj__.send(response["result"])   # resume the single yield
except StopIteration as e:
    return self.set_result(e.value)             # e.value IS the parsed result
raise ProtocolException("could not parse the cdp response:\n%s" % response)
```

**Flow:** construction consumes the FIRST yield to learn method+params (so the wire message exists before any id/socket is needed) → `Connection.send` assigns id, registers `mapper[id]=tx`, writes `tx.message` → when the response frame arrives, `listener_loop` pops `mapper[id]` and calls `tx(**message)` → `error` key sets `ProtocolException` as the future's exception; otherwise resuming the generator converts the raw result dict into the typed cdk object via StopIteration. `ProtocolException.__init__` accepts a dict (reads `message`+`code`), an object with `.to_json` (pretty-printed recursively), or plain args joined with `" | "`; `__str__` appends `[code: N]` only when a code exists.
**Invariants:** (1) **single-yield shape is load-bearing** — a two-yield adapter (yield request, then ANOTHER yield before returning) makes `__call__`'s `send()` return normally instead of raising StopIteration, so even a well-formed response raises `ProtocolException("could not parse…")` (probe-proven adversarial case, pass-21 corrected: the failure needs an UNEXHAUSTED extra yield, not merely a `r = yield …; return r` tail); porters wrapping raw JSON-RPC must re-shape to one yield + return. CAVEAT (pass-21 probe-proven): one-yield-plus-return generators complete the future NORMALLY even when the result payload fails the ported contract — `res = yield req; return res` makes StopIteration.value the SENT payload VERBATIM (`send()` returns what `__call__` passed, i.e. `response["result"]`), so `.result()` hands back the raw dict with ZERO shape validation and no ProtocolException; result validation is entirely the CALLER's job on that shape. (2) `__call__` is `**response` keyword-only — positional dict raises TypeError. (3) ERRATUM: module constant `GLOBAL_DELAY = 0.005` (:38) is DEAD — zero references anywhere in zendriver; do not "port" it as meaningful. (4) On `send()` failure the exception is RE-RAISED with `command:`/`params:` context appended to `e.message` (see websocket-dispatch-ledger).
**Probe:** real execution, no browser needed (import-by-path recipe: stub `zendriver.cdp.{target,page,browser}` attrs + `zendriver.core.util.cdp_get_module` in `sys.modules`, then `importlib.util.spec_from_file_location("zendriver.core.connection", ".../core/connection.py")`):
```bash
python3 - <<'EOF'
# after import-by-path of connection.py as C (see Source above):
def gen():
    res = yield {"method":"Page.navigate","params":{"url":"about:blank"}}
    return res["frameId"]
tx = C.Transaction(gen())
assert tx.method=="Page.navigate" and tx.params=={"url":"about:blank"}
tx.id=7; assert json.loads(tx.message)["id"]==7
try: tx({}); raise SystemExit("positional must fail")
except TypeError: pass
tx(**{"result":{"frameId":"F1"}}); assert tx.result()=="F1"
# ADVERSARIAL (corrected pass-21): the real trap is a generator that yields AGAIN
# after receiving the result — __call__'s send() then returns normally (no
# StopIteration) and falls through to ProtocolException("could not parse...").
def g2():
    r1 = yield {"method":"Y","params":{}}
    r2 = yield {"method":"Z","params":{}}   # unexhausted extra yield = adapter bug
    return r2
t=C.Transaction(g2()); t.id=9
try: t(**{"result":{}}); raise SystemExit("two-yield must fail")
except C.ProtocolException as e: assert "could not parse" in str(e.message)
# CAVEAT (pass-21 probe-proven): a ONE-yield-plus-return generator completes the
# future NORMALLY even when the result payload fails the ported contract —
# `res = yield req; return res` makes StopIteration.value the SENT payload
# VERBATIM (send() returns what __call__ passed: response["result"]), so
# .result() hands back the raw result dict with ZERO shape validation and no
# ProtocolException. Result validation is entirely the CALLER's job on this shape.
def g3():
    res = yield {"method":"W","params":{}}
    return res
t3=C.Transaction(g3()); t3(**{"result":{"unexpected":"shape"}})
assert t3.result()=={"unexpected":"shape"}, "single-yield+return surfaces raw result payload verbatim"
EOF
```
(pins: `grep -n 'class Transaction' zendriver/core/connection.py` → :82; `next(self.__cdp_obj__)` → :90; `'could not parse'` → :127.)
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "Transaction", limit: 6 });
// ext-zendriver.zendriver.core.connection.Transaction.__init__ Method zendriver/core/connection.py 83-95
// ext-zendriver.zendriver.core.connection.Transaction.__call__ Method zendriver/core/connection.py 110-128
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "ProtocolException message code", limit: 4 });
```
**Verdict:** ADOPT the pattern (generator-protocol transactions over one shared socket, keyword-only completion, error-key→typed-exception). AGPL — reimplement, never paste.
