<!-- capsule-v2 -->
# event-close-get-futures — one-shot event futures for navigation and close, with handler hygiene

**Source:** zendriver MIT `main@2c6d9c7daaab543d34e9fe2b0ef7eaa171c79760`; Codebase Memory `ext-zendriver`. **Question:** How do `Browser.get`, `Tab.close`, and the expectation objects guarantee their temporary handlers are removed?

## future + matching predicate + remove_handlers in both outcomes
**Path/Symbol:** `zendriver/core/browser.py:Browser.get` (:254-312); `zendriver/core/tab.py:Tab.close` (:945-973); `zendriver/core/expect.py` (whole file).
**Signature:** `async def get(self, url="about:blank", new_tab=False, new_window=False) -> tab.Tab`; `async def close(self) -> None`.
**Data Shape:** a `loop.create_future()` closed over by an async handler; completion condition encoded in the handler body.

### Decisive source
```python
# Tab.close — wait until OUR target is destroyed, max 10s
future = asyncio.get_running_loop().create_future()
event_type = cdp.target.TargetDestroyed
async def close_handler(event: cdp.target.TargetDestroyed) -> None:
    if future.done():
        return
    if self.target and event.target_id == self.target.target_id:
        future.set_result(event)
self.browser.connection.add_handler(event_type, close_handler)
if self.target and self.target.target_id:
    await self.send(cdp.target.close_target(target_id=self.target.target_id))
await asyncio.wait_for(future, 10)
self.browser.connection.remove_handlers(event_type, close_handler)
```

**Flow:** register → trigger (`create_target`/`navigate`/`close_target`) → await future (10s cap) → deregister. `Browser.get`'s handler ignores `TargetInfoChanged` events whose url is still `about:blank` unless navigating *to* about:blank (:279-283). The expectation classes generalize this: `RequestExpectation` full-matches URLs via `re.fullmatch(self.url_pattern, event.request.url)` (:38), then keys the response/loading futures on `request_id`; `DownloadExpectation.__aenter__` sets `set_download_behavior(behavior="deny", events_enabled=True)` and `__aexit__` restores the saved prior behavior from `tab._download_behavior`.
**Invariant:** handlers self-remove *on match* (`_remove_*_handler()` before `set_result`) AND after the await; every future callback guards `if future.done(): return` so late duplicate events can't double-set. A port that removes the handler only after `wait_for` leaks it on timeout.
**Probe:** direct tests pin all three expectations against live traffic: `tests/core/test_tab.py::test_expect_request` (:316), `::test_expect_response` (:333), `::test_expect_response_with_reload` (:349), `::test_expect_download` (:369), `::test_intercept` (:381).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "expect_request ResponseReceived future", limit: 5 });
```

## Verdict
Adopt the done-guard + double-deregistration discipline and deny-then-restore download gating; adapt timeouts; omit the reload-specific response test logic when porting the expectation API itself.
