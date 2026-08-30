<!-- capsule-v2 -->
# Web fetch content ladder — one tool call, four content shapes, every failure a ModelRetry

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How does an agent-facing URL fetcher classify responses by media type, convert them for token-efficient model consumption, and fail?

## `WebFetchLocalTool.__call__` + factory
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/common_tools/web_fetch.py:WebFetchLocalTool.__call__` (:77–138), `_TITLE_RE`/`_extract_title` (:141–147), `_clean_whitespace` (:150–151), `web_fetch_tool(...)` factory (:155–206).
**Signature:** `async def __call__(self, url: str) -> WebFetchResult | BinaryContent`.
**Data Shape:** Success returns `WebFetchResult(url, title, content)` TypedDict OR raw `BinaryContent(data, media_type)`; ALL transport/policy failures (`ValueError`, `httpx.HTTPStatusError`, `httpx.RequestError`) raise `ModelRetry(f'Failed to fetch {url}: {e}')`.

### Decisive source
```python
# web_fetch.py:110-135 — content-type ladder over SSRF-safe download
media_type = response.headers.get('content-type', '').split(';')[0].strip().lower()
if not media_type or is_text_like_media_type(media_type):
    text = response.text
    if media_type in ('text/markdown', 'text/x-markdown'):
        content = text                                    # server already sent markdown
    elif not media_type or media_type in ('text/html', 'application/xhtml+xml'):
        title = _extract_title(text)
        content = md(text, strip=['img', 'script', 'style'])  # HTML → markdown, scripts stripped
    elif media_type == 'application/json':
        try:
            parsed = json.loads(text)
            content = f'```json\n{json.dumps(parsed, indent=2)}\n```'  # pretty-fenced
        except (json.JSONDecodeError, ValueError):
            content = text                                # invalid JSON passes through verbatim
    else:
        content = text                                    # plain text / other text types
else:
    return BinaryContent(data=response.content, media_type=media_type or 'application/octet-stream')
content = _clean_whitespace(content)                      # collapse 3+ newlines → 2
if self.max_content_length is not None and len(content) > self.max_content_length:
    content = content[: self.max_content_length] + '\n\n[Content truncated]'
```

**Flow:** request with `Accept: text/markdown, text/html;q=0.9, */*;q=0.8` (markdown-first saves tokens against servers like Cloudflare/Vercel/Mintlify that honor it) → `safe_download` enforces SSRF policy (scheme allowlist, private-IP block unless `allow_local_urls`, cloud-metadata always blocked, DNS pre-resolution, byte cap before buffering, optional allowed/blocked domain lists) → ladder above → truncate tail-appended marker.

**Invariant:** Every failure mode is a ModelRetry, never an exception escape — the MODEL sees "fetch failed, fix your args" instead of the run crashing. Domain filters match hostname only (not scheme/port), so credential-bearing headers are dangerous with an open domain list — hence redirect-sensitive headers (Authorization/Cookie/Proxy-Authorization) forward only same-origin or http→https upgrades. Binary passthrough keeps provider-native processing (PDFs/images) alive rather than force-decoding garbage.

**Probe:** `tests/test_web_fetch.py::test_fetch_html_title_with_whitespace` (:47), `test_fetch_html_collapses_excessive_newlines` (:90), `test_fetch_json` (:106), `test_fetch_invalid_json` (:126), `test_fetch_no_content_type` (:162), `test_content_truncation` (:182).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "web_fetch_tool safe_download WebFetchLocalTool markdownify", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the media-type ladder, markdown-first Accept header, all-errors-are-ModelRetry posture, and truncate-with-suffix. Adapt converter choice (markdownify vs your HTML pipeline) and limits freely. Omit the SSRF implementation itself — `_ssrf.safe_download` is its own reusable primitive.
