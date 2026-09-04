<!-- capsule-v2 -->
# Outbound request plane — how must consent-check and page-fetch HTTP be constructed so robots.txt is evaluated from the same network vantage as the actual request?

**Source:** modelcontextprotocol/servers MIT `main@599dafc1054550a6eeb87a6545c1e1b03b3ca827`; Codebase Memory `servers`. **Question:** where do proxy, redirects, timeouts, and robots-URL derivation live so a consent gate cannot silently disagree with the fetch it guards?

## Per-hop fresh clients with identical proxy; robots URL keeps only scheme+netloc
**Path/Symbol:** `src/fetch/src/mcp_server_fetch/server.py` — `get_robots_txt_url` :48–63; consent client :75–81; page client :119–126; comment-strip before Protego :95–98; status/error mapping :82–93 and :127–133; startup knobs via argparse in `src/fetch/src/mcp_server_fetch/__init__.py` `main` :12–21.
**Signature:** `get_robots_txt_url(url: str) -> str`; `check_may_autonomously_fetch_url(url: str, user_agent: str, proxy_url: str | None = None) -> None`; `fetch_url(url, user_agent, force_raw=False, proxy_url=None)`; `main()` wiring `--user-agent/--ignore-robots-txt/--proxy-url` → `asyncio.run(serve(...))`.
**Data Shape:** both outbound hops construct their own short-lived `httpx.AsyncClient(proxy=proxy_url)` inside an `async with` block — no shared session, no connection reuse across hops; the SAME optional `proxy_url` closure value feeds both.

### Decisive source
```python
# server.py:57-61 — robots URL derivation: scheme + netloc ONLY (port preserved)
    parsed = urlparse(url)
    robots_url = urlunparse((parsed.scheme, parsed.netloc, "/robots.txt", "", "", ""))

# server.py:75-81 — the CONSENT hop: same proxy, follow_redirects, UA header; NO timeout arg
    async with AsyncClient(proxy=proxy_url) as client:
        try:
            response = await client.get(
                robot_txt_url,
                follow_redirects=True,
                headers={"User-Agent": user_agent},
            )

# server.py:119-126 — the FETCH hop: identical construction PLUS timeout=30
    async with AsyncClient(proxy=proxy_url) as client:
        try:
            response = await client.get(
                url,
                follow_redirects=True,
                headers={"User-Agent": user_agent},
                timeout=30,
            )
```

**Flow:** tool call → (unless `--ignore-robots-txt`) derive `robots.txt` URL from the TARGET url by keeping exactly `(scheme, netloc)` and hard-coding path `/robots.txt` while dropping path/query/fragment → GET it through `AsyncClient(proxy=proxy_url)` with `follow_redirects=True` and the autonomous UA → strip full-line `#` comments from the body text BEFORE handing it to `Protego.parse` (:95–98) → on pass, the actual page GET runs through a FRESH client built with the SAME `proxy_url`, plus `timeout=30`. Transport errors (`HTTPError`) and any `status >= 400` map to `McpError(INTERNAL_ERROR)` at BOTH hops.
**Invariant:** **proxy parity** — the robots.txt lookup and the real fetch must traverse identical network conditions (same proxy), otherwise the consent decision is made from a different vantage point than the action it authorizes (test-pinned byte-exactly). Redirect-following matches too. Honest asymmetry to know about: only the page hop sets `timeout=30`; the robots hop is unbounded — if you port this, decide deliberately whether that is acceptable for your environment rather than copying it blindly. Robots-URL derivation is host-scoped by design: policies live at the origin root, so deep paths, queries, fragments, and non-default ports resolve per the pinned matrix (ports ride `netloc`, everything after the authority is discarded).
**Probe:** `src/fetch/tests/test_server.py::TestFetchUrl.test_fetch_with_proxy` (:306–326 — `mock_client_class.assert_called_once_with(proxy="http://proxy.example.com:8080")` pins the exact client-construction kwarg), `::TestGetRobotsTxtUrl` six variants (:19–47 — simple/deep-path/query/port/fragment/http all collapse to `scheme://host[:port]/robots.txt`), `::TestCheckMayAutonomouslyFetchUrl` (:95–184 — 404/other-4xx allow vs 401/403 refuse through the same client seam). Live-run 2026-08-25: **20/20 passed**.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "servers", query: "AsyncClient proxy robots fetch_url check_may_autonomously_fetch_url" });
await mcp.codebase_memory.get_code_snippet({ project: "servers", qualified_name: "servers.src.fetch.src.mcp_server_fetch.server.get_robots_txt_url" });
```
(Live-executed at `599dafc1`: search returned the fetch seam family led by test_fetch_with_proxy :306–326 and get_robots_txt_url :48–63; snippet resolved byte-consistent with the disk read.)

## Verdict
Adopt per-hop client construction with proxy parity between any pre-flight consent lookup and the guarded request, redirect behavior matched on both sides, and origin-root robots/policy URL derivation that preserves scheme+host(+port) while discarding everything after the authority. Adopt preprocessing policy files (comment stripping) before feeding them to a parser when your parser's spec requires it. Adapt timeouts deliberately — the reference's unbounded robots hop is a quirk, not a pattern; give both hops explicit deadlines in production. Omit httpx specifics if your stack differs; preserve only the parity invariant and the INTERNAL_ERROR mapping for transport/remote failures (argument-shape failures stay INVALID_PARAMS per `tool-guard-python`). Direct-test coverage complete at `599dafc1`.
