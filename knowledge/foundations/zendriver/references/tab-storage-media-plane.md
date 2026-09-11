<!-- capsule-v2 -->
# tab-storage-media-plane — localStorage origin math, download path latching, and the capture family

**Source:** zendriver MIT `main@2c6d9c7daaab543d34e9fe2b0ef7eaa171c79760`; Codebase Memory `ext-zendriver`. **Question:** How are per-origin storage and page-capture operations addressed without a URL bar?

## Origin = scheme://host:port via split("/", 3); downloads latch once
**Path/Symbol:** `zendriver/core/tab.py:get_local_storage` (:1653-1674) / `set_local_storage` (:1676-1703), `set_download_path` (:1451-1466) + `download_file` (:1273-1332), `save_snapshot` (:1334-1349), `screenshot_b64`/`save_screenshot` (:1351-1428), `print_to_pdf` (:1430-1449), `get_all_urls` (:1477-1507).
**Signature:** `async def get_local_storage(self) -> dict[str, str]`; `async def set_download_path(self, path: PathLike)`; `async def screenshot_b64(self, format="jpeg", full_page=False) -> str`.
**Data Shape:** `StorageId(is_local_storage=True, security_origin=origin)`; `_download_behavior: List[str] | None` on the connection mirrors the CDP-side behavior.

### Decisive source
```python
# there must be a better way...
origin = "/".join(self.url.split("/", 3)[:-1] if self.url else [])
items = await self.send(cdp.dom_storage.get_dom_storage_items(
    cdp.dom_storage.StorageId(is_local_storage=True, security_origin=origin)))
```
and the download default + anchor-click JS:
```python
if not self._download_behavior:
    directory_path = pathlib.Path.cwd() / "downloads"
    directory_path.mkdir(exist_ok=True)
    await self.set_download_path(directory_path)
    warnings.warn(f"no download path set, so creating and using a default of{directory_path}")
```
Screenshot empty-data guard (:1380-1383): raise ProtocolException "could not take screenshot. most possible cause is the page has not finished loading yet."

**Flow:** both storage ops first `await self.wait()` when target url is unset (ensures a real origin exists). `set_download_path` sends `browser.set_download_behavior("allow", path)` AND caches it in `_download_behavior`; `download_file` lazily defaults to `./downloads`, derives filename from URL (stripping query), then injects an anchor-click fetch snippet via `runtime.call_function_on` bound to `<body>`. Captures share a contract: update target first (`await self.sleep()`), send capture command, treat falsy data as not-loaded-yet failure; auto filenames are `{hostname}__{last_path_part}_{YYYY-MM-DD_HH-MM-SS}`.
**Invariant:** the origin string must include port (split at the 3rd slash keeps scheme+host+port together) — dropping port silently reads a different storage partition for non-default ports. And `get_all_urls(absolute=True)` filters candidates by requiring `http`, `//`, or `/` substrings then urljoins against `url.rsplit("/")[:3]` — relative-scheme URLs survive, fragments don't.
**Probe:** static anchors at pin: `grep -n 'json/{endpoint}' zendriver/core/browser.py` → :848 (HTTPApi twin of this addressing style); direct tests exercise captures in `tests/docs/tutorials/test_api_responses_tutorial.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "get_local_storage set_download_path", limit: 5 });
```

## Verdict
Adopt origin math and behavior-latching exactly; adapt the anchor-download JS to your CSP reality (it needs inline handlers); keep the not-loaded-yet ProtocolException semantics so callers can retry.
