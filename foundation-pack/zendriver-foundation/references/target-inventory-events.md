<!-- capsule-v2 -->
# target-inventory-events — how does browser.targets stay true while tabs open, close, and crash?

**Source:** zendriver MIT `main@2c6d9c7daaab543d34e9fe2b0ef7eaa171c79760`; Codebase Memory `ext-zendriver`. **Question:** How are targets reconciled from both event pushes and explicit refreshes?

## One handler, four events, mutex-serialized
**Path/Symbol:** `zendriver/core/browser.py:Browser._handle_target_update` (:190-252), `update_targets` (:552-573), `tabs`/`main_tab` (:151-167), `get` (:254-312).
**Signature:** `async def _handle_target_update(self, event: TargetInfoChanged | TargetDestroyed | TargetCreated | TargetCrashed) -> None`.
**Data Shape:** `self.targets: List[Connection]`; Tab websocket URLs are synthesized as `ws://{host}:{port}/devtools/{type or 'page'}/{target_id}` — with the in-source note *"all types are 'page' internally in chrome apparently"* (:233 and :565).

### Decisive source
```python
async with self._update_target_info_mutex:
    if isinstance(event, cdp.target.TargetInfoChanged):
        current_tab = next(filter(lambda item: item.target_id == target_info.target_id, self.targets))
        ...
        current_tab.target = target_info
    elif isinstance(event, cdp.target.TargetCreated):
        new_target = Tab((f"ws://{host}:{port}/devtools/{type_ or 'page'}/{target_info.target_id}"), ...)
        self.targets.append(new_target)
    elif isinstance(event, cdp.target.TargetDestroyed):
        current_tab = next(filter(lambda item: item.target_id == event.target_id, self.targets))
        self.targets.remove(current_tab)
```

**Flow:** event handlers mutate the inventory under one asyncio.Lock (handlers run as separate tasks via the listener, so races are real). `update_targets()` is the poll-side twin: `target.get_targets()` then in-place `__dict__.update` for known ids else append a fresh Connection. `Browser.get()` navigates the first page tab and awaits a one-shot `TargetInfoChanged` future with a 10s cap — deliberately ignoring startup `about:blank` transitions (:279-283). `main_tab` sorts page-typed targets first; iteration (`__iter__/__next__`) walks `tabs` relative to main.
**Invariant:** `TargetCrashed` is accepted by the handler but has **no branch** — crashed targets linger until destroyed. A porter adding exhaustive isinstance handling should keep that asymmetry in mind rather than assume every event type mutates state.
**Probe:** direct tests pin inventory behavior: `tests/core/test_browser.py::test_update_target_sets_target_title` (:39), `::test_browser_stop_can_be_called_on_a_closed_connection` (:46); static anchor `grep -c "all types are" zendriver/core/browser.py` → 2.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "_handle_target_update TargetCreated", limit: 5 });
```

## Verdict
Adopt the dual event+poll reconciliation and single-mutex discipline; adapt the URL synthesis if your CDP build distinguishes target types; document the Crashed no-op when porting.
