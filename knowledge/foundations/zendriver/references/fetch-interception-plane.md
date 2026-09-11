<!-- capsule-v2 -->
# fetch-interception-plane — BaseFetchInterception lifecycle: pause, inspect, then continue/fulfill/fail

**Source:** zendriver MIT `main@2c6d9c7daaab543d34e9fe2b0ef7eaa171c79760`; Codebase Memory `ext-zendriver`. **Question:** How does the async-CM interception keep the browser unblocked and the user block clean?

## enable(pattern) → RequestPaused future → decision verbs
**Path/Symbol:** `zendriver/core/intercept.py:BaseFetchInterception` (:10-171); factory `Tab.intercept` (`tab.py:1254-1271`).
**Signature:** `BaseFetchInterception(tab, url_pattern: str, request_stage: RequestStage, resource_type: ResourceType)`; verbs `continue_request(...)`, `fulfill_request(...)`, `fail_request(error_reason)`, plus `async response_body`.
**Data Shape:** one `response_future: asyncio.Future[cdp.fetch.RequestPaused]`; every verb extracts `request_id` from that event.

### Decisive source
```python
async def _setup(self) -> None:
    await self.tab.send(cdp.fetch.enable([RequestPattern(
        url_pattern=self.url_pattern,
        request_stage=self.request_stage,
        resource_type=self.resource_type)]))
    self.tab.add_handler(cdp.fetch.RequestPaused, self._response_handler)

async def _teardown(self) -> None:
    self._remove_response_handler()
    await self.tab.send(cdp.fetch.disable())

async def reset(self) -> None:
    self.response_future = asyncio.Future()
    await self._teardown()
    await self._setup()
```

**Flow:** `__aenter__` enables fetch with exactly one RequestPattern (URL + stage + resource type) and registers a handler that removes itself then resolves the future. The paused request BLOCKS the browser's fetch until a decision verb is sent — `response_body` calls `fetch.get_response_body(request_id)`; `continue_request` may rewrite url/method/post_data/headers; `fulfill_request` synthesizes a full response; `fail_request` aborts with an ErrorReason. Handler removal happens in `_response_handler` *before* set_result, so late duplicate pauses don't re-trigger.
**Invariant:** while paused, ALL other network on that pattern stalls — a port that awaits something else before issuing continue/fulfill/fail deadlocks the page. And `reset()` is the only sanctioned reuse path (fresh future + re-setup).
**Probe:** direct test drives interception against httpbin: `tests/core/test_tab.py::test_intercept` (:381); static anchor at pin: `grep -n 'fullmatch' zendriver/core/expect.py` → :38 (the expectation-family cousin uses fullmatch, interception itself uses server-side pattern matching).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "BaseFetchInterception RequestPaused", limit: 5 });
```

## Verdict
Adopt the CM lifecycle and self-removing handler; adapt pattern granularity per need; never port the pause-without-decision path — it is a hang by design.
