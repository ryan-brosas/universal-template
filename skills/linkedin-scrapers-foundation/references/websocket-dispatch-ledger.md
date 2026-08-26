<!-- capsule-v2 -->
# CDP websocket dispatch ledger — how do concurrent commands share ONE socket without interleaving responses, and why does the id map double as a leak guard?

**Source:** zendriver AGPL-3.0 — PATTERNS ONLY, never copy verbatim. `main@2c6d9c7d`; Codebase Memory project `ext-zendriver`. **Question:** what is the full lifecycle of a `Connection.send()` call and of every frame the listener reads, including the special ids that must never crash dispatch?

## One mutex-guarded counter, one mapper, one reader loop
**Path/Symbol:** `zendriver/core/connection.py:Connection.send` (:535-585), `_send_oneshot` (:710-723), `feed_cdp` (:462-475), `aopen/aclose` (:417-456), `Listener.listener_loop` (:773-886), `Listener.__init__` (:726-751).
**Signature:** `async send(cdp_obj, _is_update=False) -> T`; `_send_oneshot(cdp_obj) -> Any` (id **-2**, swallows ProtocolException); `feed_cdp(cdp_obj)` — SYNC fire-and-forget via `asyncio.ensure_future(self.send(...))`.
**Data Shape:** `mapper: dict[int, Transaction]` (in-flight + the -2 slot); `__count__: itertools.count(0)` reset to 0 whenever `mapper` is found EMPTY (post-crash id hygiene); `_current_id_mutex: asyncio.Lock` guards `next()`; socket constants: `MAX_SIZE = 2**28` (256 MiB frame cap — big DOM dumps), `PING_TIMEOUT = 900`s (15-min keepalive). `Listener.history: deque(max 1000)` is declared but NEVER appended to (dead debug buffer — erratum); `idle` event semantics are owned by idle-breathe-readiness.

### Decisive source
```python
# Connection.send (:564-585)
tx = Transaction(cdp_obj); tx.connection = self
if not self.mapper:
    self.__count__ = itertools.count(0)
async with self._current_id_mutex:
    tx.id = next(self.__count__)
self.mapper.update({tx.id: tx})
if not _is_update:
    domain_name, _, action = tx.method.partition(".")
    if action == "enable":  self._update_manual_domain(domain_name, action)
    await self._register_handlers()
    if action == "disable": self._update_manual_domain(domain_name, action)
await self.websocket.send(tx.message)
try:
    return await tx
except ProtocolException as e:
    e.message += f"\ncommand:{tx.method}\nparams:{tx.params}"; raise

# Listener.listener_loop response arm (:810-829)
tx = self.connection.mapper.pop(message["id"])   # pop BEFORE completion — zxsleebu memory-leak fix
tx(**message)
...
if message["id"] == -2:                          # oneshot slot survives across frames
    maybe_tx = self.connection.mapper.get(-2) ...
```

**Flow:** send → lazy `aopen()` (websocket connect with MAX_SIZE/PING_TIMEOUT; Listener spawned; handlers re-registered because the BROWSER forgets enabled domains after reconnect — see lazy-domain-enablement) → owner-config prep latches (`_prepare_expert/_prepare_headless`, see headless-expert-prep-latches) → fresh Listener if dead → Transaction → id under mutex → mapper insert → (non-internal sends trigger domain bookkeeping around `_register_handlers`) → wire write → await future. Read side: every frame is JSON-parsed; `id` present → command response → **pop then complete** (`error` key ⇒ ProtocolException set as exception; unparseable result dict ⇒ ProtocolException raised from `__call__`, caught by nobody but the awaiting sender whose re-raise appends method/params context); unknown id or absent -2 slot → `continue`, never KeyError; no `id` → event arm → parse_json_event → EventTransaction inserted into the SAME mapper (so events also reset/advance the shared counter) → fan-out to per-type handlers, each callback wrapped in try/except TypeError trying `(event, connection)` then `(event)` signatures, sync callbacks pushed through `asyncio.to_thread`, one bad callback logged+re-raised without killing the loop.
**Invariants:** (1) responses are matched ONLY by numeric id — order-free multiplexing over one socket; (2) the mapper pop happens BEFORE completion (the upstream-cited memory-leak fix) — anything that completes without popping leaks forever, so porters must keep pop→complete atomic in the reader; (3) `-2` is a reserved oneshot slot reused across calls and its absence mid-race must be a silent continue; (4) `feed_cdp` exists for `fetch.RequestPaused`-style BLOCKING interception where you must answer the browser without awaiting (sync ensure_future); (5) `aclose` cancels the listener FIRST and clears both domain lists so a later `aopen` re-registers cleanly.
**Probe:** real execution — FakeWS feeding four frames through the REAL auto-started listener task:
```bash
python3 - <<'EOF'
# import-by-path C (stub cdp surface) per cdp-transaction-generator-protocol Source
class FakeWS:
    def __init__(s, f): s.frames=list(f)
    async def recv(s):
        if s.frames: return s.frames.pop(0)
        await asyncio.Event().wait(); return ""
async def main():
    real_tx = C.Transaction(gen()); real_tx.id=42
    conn = C.Connection.__new__(C.Connection)
    conn.websocket=None; conn.mapper={}; conn.handlers={}; conn.listener=None
    conn.mapper[42]=real_tx
    conn.websocket = FakeWS([json.dumps({"id":42,"result":{"frameId":"F9"}}),
                             json.dumps({"id":-2,"result":{}}),
                             json.dumps({"id":999,"result":{}})])
    L = C.Listener(conn)                    # ctor REQUIRES a running loop
    await asyncio.wait_for(real_tx, 3.0)    # real listener_loop completes it
    assert real_tx.result()=="F9" and 42 not in conn.mapper
    L.cancel()
asyncio.run(main())
EOF
```
(pins: `grep -n 'mapper.pop' zendriver/core/connection.py` → :815; `grep -n 'MAX_SIZE' zendriver/core/connection.py` → :39,:428; `grep -n 'PING_TIMEOUT' zendriver/core/connection.py` → :40,:427; `grep -n 'ensure_future' zendriver/core/connection.py` → :475; `grep -n 'history' zendriver/core/connection.py` → :729,:730,:890 only.)
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "listener_loop mapper pop transaction", limit: 8 });
// ext-zendriver.zendriver.core.connection.Listener.listener_loop Method zendriver/core/connection.py 773-886
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "send_oneshot feed_cdp ensure_future", limit: 6 });
// Connection.feed_cdp Method zendriver/core/connection.py 462-475; _send_oneshot Method 710-723
```
**Verdict:** ADOPT the pattern (id-mutex + pop-before-complete reader loop + reserved-id tolerance + sync fire-and-forget escape hatch for blocking interception). AGPL — reimplement, never paste.
