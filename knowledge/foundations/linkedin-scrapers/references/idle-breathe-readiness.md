<!-- capsule-v2 -->
# Idle-breathe readiness loop — when is a page "settled" without a fixed sleep?

**Source:** zendriver AGPL-3.0 — PATTERNS ONLY, never copy verbatim. `main@2c6d9c7d`; Codebase Memory `ext-zendriver`. **Question:** how do you wait for network/DOM quiet WITHOUT hard-coded sleeps, and why does the threshold differ between REPL and production?

## Event-driven idle latch
**Path/Symbol:** `zendriver/core/connection.py:Listener` (:726-797 idle logic), `Connection.wait` (:477-506), `Connection.__await__` (:520-527).
**Signature:** `Listener(connection)` starts an asyncio task; `wait(t=None)` awaits `listener.idle` optionally floored to `t` seconds; `await connection` == `await connection.wait()`.
**Data Shape:** `idle: asyncio.Event`; `_time_before_considered_idle`: **0.75s in interactive mode** (`sys.ps1` present or `sys.flags.interactive`) vs **0.10s in production** — measured upstream as ~5s saved per demo script. A deque `history` (max 1000) buffers recent messages for debugging.

### Decisive source
```python
is_interactive = getattr(sys, "ps1", sys.flags.interactive)
self._time_before_considered_idle = 0.10 if not is_interactive else 0.75
# listener_loop:
msg = await asyncio.wait_for(self.connection.websocket.recv(), self.time_before_considered_idle)
except asyncio.TimeoutError:
    self.idle.set()      # silence FOR one window => idle
    continue             # loop keeps running; next message clears idle again
self.idle.clear()
```

**Flow:** every received frame clears `idle`; when NO frame arrives within the window, `idle.set()` and the loop continues listening. `wait(t)`: refreshes target info, waits `idle`, and if a numeric floor was given keeps sleeping until `t` elapsed even if idle fired early; `TimeoutError` inside the floor branch is deliberately swallowed ("explicit time given … bail out early" — the floor already guarantees the budget).
**Invariant:** idle is a SLIDING window, not a countdown — one stray event restarts the whole quiet period; and the listener task NEVER exits on idle (only cancel/close/error stops it), so `idle` can flap freely. Porters who implement idle as `sleep(N)` lose both the interactivity and the early-exit economics.
**Probe:** no dedicated upstream unit test (coverage caveat) → deterministic pins (anchored at the `zendriver/` package dir): `grep -n 'ps1' core/connection.py` → :745; `grep -n 'self.idle.set()' core/connection.py` → :783; `grep -n 'idle.wait()' core/connection.py` → :494,:498. Behavioral adjacency: `tests/core/test_tab.py::test_wait_for_ready_state` exercises the sibling ready-state poller live.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "time_before_considered_idle listener_loop idle", limit: 5 });
```

## Verdict
Adopt: sliding-window quiet detection with an interactive-vs-production dual threshold; `await conn` ergonomics mapping to "settle". Adapt thresholds to your event volume (0.10/0.75 were tuned against Chrome's event rate). Omit the debug history deque. Cross-reference: this is the same family as browser-harness-js's json-navigation-doctrine ("the poll IS the head validation") — here the recv-timeout IS the quiet detector. Coverage: source-pinned only; upstream has no direct test for Listener timing.
