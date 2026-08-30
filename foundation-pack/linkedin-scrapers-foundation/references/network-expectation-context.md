<!-- capsule-v2 -->
# Network expectation context manager — how do you await a specific request/response and read its body without racing the page?

**Source:** zendriver AGPL-3.0 — PATTERNS ONLY. `main@2c6d9c7d`; Codebase Memory `ext-zendriver`. **Question:** how do you wait for a particular network request/response, read its body, and (for fetch) intercept/modify it — all without missing the event or deadlocking?

## Future-backed event expectation + body-after-loading-finished + fetch interception
**Path/Symbol:** `zendriver/core/expect.py:BaseRequestExpectation` (:9-150), `RequestExpectation`/`ResponseExpectation` (:152-186), `DownloadExpectation` (:188-233); `core/intercept.py:BaseFetchInterception` (:10-171); factory methods `Tab.expect_request/expect_response/expect_download/intercept` (`core/tab.py:1224-1271`).
**Signature:** `async with tab.expect_request(url_pattern) as req: ... await req.value`; `async with tab.intercept(url_pattern, RequestStage, ResourceType) as it: ... await it.response_body`.
**Data Shape:** `BaseRequestExpectation` holds three asyncio futures — `request_future` (RequestWillBeSent), `response_future` (ResponseReceived), `loading_finished_future` (LoadingFinished) — plus the captured `request_id`. URL matching is `re.fullmatch`. `DownloadExpectation` sets `browser.set_download_behavior(behavior="deny", events_enabled=True)` on enter and restores the prior behavior on exit.

### Decisive source
```python
async def _request_handler(self, event):
    if re.fullmatch(self.url_pattern, event.request.url):
        self._remove_request_handler()          # fire once — remove self immediately
        self.request_id = event.request_id
        self.request_future.set_result(event)
# response_body: must wait for LoadingFinished BEFORE fetching the body
request_id = (await self.response_future).request_id
await self.loading_finished_future             # body not available until load completes
body = await self.tab.send(cdp.network.get_response_body(request_id=request_id))
```

**Flow:** entering the context manager registers request/response/loading-finished handlers and matches by fullmatch (request) then by `request_id` (response/loading). Each handler REMOVES ITSELF on first match so the expectation fires once and is reusable via `reset()` (fresh futures + re-register). `response_body` awaits `LoadingFinished` before `Network.getResponseBody` — the body is not readable until the load completes. `BaseFetchInterception` uses `Fetch.enable` with a `RequestPattern` (url+stage+resource_type), collects `RequestPaused`, and exposes `response_body`, `fail_request`, `continue_request`, `fulfill_request`, `continue_response` — enabling request blocking/modification/fulfillment. `DownloadExpectation` flips download behavior to `deny` (so the download doesn't hit disk) and captures `DownloadWillBegin`.
**Invariant:** the request handler removes itself on the FIRST fullmatch — so an expectation is single-shot per URL match unless `reset()` is called (the `test_expect_response_with_reload` test proves reset works across a reload). Body reads MUST gate on `LoadingFinished` or you get an empty/partial body. This is the CDP-native cousin of linkedin-scrapers' response-interception and request-interception-budget capsules (the LinkedIn suites intercept via CDP Fetch/Network the same way).
**Probe:** REAL tests — `tests/core/test_tab.py:316 test_expect_request`, `:333 test_expect_response`, `:349 test_expect_response_with_reload` (reset), `:369 test_expect_download`, `:381 test_intercept`, `:399 test_intercept_with_reload` (reset). Deterministic pin (anchored at the `zendriver/` package dir): `grep -n 'loading_finished_future' core/expect.py` → :28,:146-147.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "expect_response BaseRequestExpectation loading_finished_future", limit: 5 });
```

## Verdict
Adopt: future-backed single-shot event expectations with body-after-load gating and self-removing handlers; fetch interception for block/modify/fulfill. Adapt the URL-matching semantics (fullmatch here) to your needs. Omit the download-denial behavior unless you need it. Coverage: directly test-pinned (6 live tests).
