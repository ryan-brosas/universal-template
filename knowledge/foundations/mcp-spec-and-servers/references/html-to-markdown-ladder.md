<!-- capsule-v2 -->
# HTML→markdown extraction ladder — how do you turn an arbitrary fetched web page into LLM-consumable markdown while keeping an honest raw fallback for payloads that cannot be simplified?

**Source:** modelcontextprotocol/servers MIT `main@599dafc1054550a6eeb87a6545c1e1b03b3ca827`; Codebase Memory `servers`. **Question:** what is the conversion ladder for fetched web content, when does it apply, and how must failure and raw modes be labeled so the model never mistakes degraded output for clean text?

## Readability-first simplification, then markdownify; a three-way HTML sniff decides the ladder
**Path/Symbol:** `src/fetch/src/mcp_server_fetch/server.py` — `extract_content_from_html` :27–45; `fetch_url` dispatch :135–148.
**Signature:** `extract_content_from_html(html: str) -> str`; `fetch_url(url: str, user_agent: str, force_raw: bool = False, proxy_url: str | None = None) -> Tuple[str, str]` returning `(content, prefix)`.
**Data Shape:** input is the raw response body string plus response headers; output is either simplified markdown with an EMPTY prefix (ladder succeeded) or the untouched body with a non-empty explanatory prefix (raw path). The prefix is the honest channel: empty means "this is clean markdown", any text means "this could not be simplified".

### Decisive source
```python
# server.py:36-45 — readability FIRST, then markdownify ATX on the simplified fragment
    ret = readabilipy.simple_json.simple_json_from_html_string(
        html, use_readability=True
    )
    if not ret["content"]:
        return "<error>Page failed to be simplified from HTML</error>"
    content = markdownify.markdownify(
        ret["content"],
        heading_style=markdownify.ATX,
    )
    return content

# server.py:137-148 — three-way HTML sniff and the labeled raw escape hatch
    content_type = response.headers.get("content-type", "")
    is_page_html = (
        "<html" in page_raw[:100] or "text/html" in content_type or not content_type
    )

    if is_page_html and not force_raw:
        return extract_content_from_html(page_raw), ""

    return (
        page_raw,
        f"Content type {content_type} cannot be simplified to markdown, but here is the raw content:\n",
    )
```

**Flow:** GET succeeds → read body + content-type header → classify with THREE independent signals (`"<html"` literal within the first 100 chars OR declared `text/html` OR missing/empty content-type — absence of the header defaults INCLUSIVELY toward the markdown ladder) → if classified HTML and the caller did not force raw, simplify with readability-lxml (`use_readability=True`) then convert the surviving fragment to ATX-headline markdown → otherwise return the body verbatim with the "cannot be simplified" prefix. JSON needs NO special case: `application/json` fails all three sniff arms and falls through to raw naturally (test-pinned).
**Invariant:** conversion failure NEVER raises inside the ladder — an empty readability result degrades to a literal `<error>Page failed to be simplified from HTML</error>` string that rides inside successful tool output, because a failed simplification is still a successful fetch worth showing the model. The raw path always self-labels via its prefix even when simplification WAS possible (`force_raw=True` is a user override, and the prefix honestly says the payload is unsimplified). Never let the model see unexplained raw bytes.
**Probe:** `src/fetch/tests/test_server.py::TestExtractContentFromHtml.test_empty_content_returns_error` (:84–88 — empty HTML yields `"<error>" in result`, pinning the error-as-string sentinel), `::TestFetchUrl.test_fetch_json_returns_raw` (:247–267 — JSON returns body verbatim + "cannot be simplified" prefix), `::test_fetch_html_page_raw` (:223–244 — force_raw returns original HTML with the same prefix), `::test_fetch_html_page` (:191–220 — markdown path returns `prefix == ""`). Live-run 2026-08-25: **20/20 passed** (throwaway venv; readabilipy's Node-backed readability path exercised).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "servers", query: "extract_content_from_html fetch_url markdown readability", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "servers", qualified_name: "servers.src.fetch.src.mcp_server_fetch.server.fetch_url" });
```
(Live-executed at `599dafc1`: BM25 led by extract_content_from_html :27–45 / fetch_url :111–148 among 151 hits; get_code_snippet returned fetch_url byte-identical to disk.)

## Verdict
Adopt the two-stage ladder (readability-style main-content extraction BEFORE markdown conversion — converting whole DOMs buries models in nav/chrome) and the three-way inclusive sniff with missing-content-type defaulting to "try markdown". Adopt the prefix contract: empty prefix = clean conversion, non-empty = verbatim payload with an explicit reason. Adopt error-as-string sentinels ONLY for post-fetch degradation that is still worth displaying; transport failures belong one layer up as protocol errors (see `tool-guard-python`). Adapt which extractor/converter libraries you use — the invariant is stage ORDER and honest labeling, not these specific packages. Omit nothing for JSON APIs: they are handled correctly by NOT special-casing them. Coverage caveat: `serve()`/`call_tool()` wiring itself has no upstream direct tests; the ladder functions above are fully pinned at `599dafc1`.
