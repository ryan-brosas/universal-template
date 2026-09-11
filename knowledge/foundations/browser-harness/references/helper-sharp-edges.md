<!-- capsule-v2 -->
# Helper sharp-edge contracts — what surprising return shapes and hidden routings must callers know?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** Where do page_info, capture_screenshot, and http_get deviate from their obvious semantics, and why?

## Dialog short-circuit / LLM-size clamp / key-gated proxy
**Path/Symbol:** `src/browser_harness/helpers.py:page_info/capture_screenshot/http_get` (:130-147, :242-254, :498-515).
**Signature:** `page_info() -> {url,title,w,h,sx,sy,pw,ph}` OR `{dialog: {...}}`; `capture_screenshot(path=None, full=False, max_dim=None)`; `http_get(url, headers=None, timeout=20)`.
**Data Shape:** max_dim PIL-thumbnails only when exceeded (docstring: keep under 2000px-per-side limits some image-aware LLMs enforce; suggested 1800 on 2× displays); http_get sends UA + Accept-Encoding gzip and decompresses manually on `Content-Encoding: gzip`.

### Decisive source
```python
dialog = _send({"meta": "pending_dialog"}).get("dialog")
if dialog:
    return {"dialog": dialog}
expression = "JSON.stringify({url:location.href,...})"
return json.loads(_runtime_evaluate(expression))
```

**Flow:** page_info asks the daemon FIRST whether a native alert/confirm/prompt/beforeunload is open — returning `{dialog}` INSTEAD of page data because the page's JS thread is frozen until handled (Runtime.evaluate would hang); screenshots decode base64 to disk with optional downsize; http_get routes through fetch-use proxy (bot detection/residential proxies/retries) ONLY when BROWSER_USE_API_KEY is set, ImportError falls back to local urllib.
**Invariant:** A frozen JS thread makes ordinary probes HANG rather than fail — the dialog pre-check converts a hang into structured data; image clamping serves model-side vision limits, not browser ones; proxy routing upgrades scraping reliability when credentials exist but must degrade cleanly without them.
**Probe:** `tests/unit/test_helpers.py:56-77` pins page_info's clear error on JS exceptions; max_dim pinned at :20-29 (4592→1800, small images untouched, default no-resize). The `{dialog}` return itself has no direct helper test — coverage caveat; anchors verified at source :141-146.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "page_info dialog screenshot http get", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt the dialog-first probe pattern for any page-introspection helper. Adapt clamping limits to your vision consumer. Omit proxy routing without an equivalent service.
