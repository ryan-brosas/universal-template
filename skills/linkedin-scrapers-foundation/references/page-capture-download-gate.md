<!-- capsule-v2 -->
# Page capture & artifact export — how do you persist a CDP page as MHTML/screenshot/PDF, and how do downloads get a path at all?

**Source:** zendriver AGPL-3.0 — PATTERNS ONLY. `main@2c6d9c7d`; Codebase Memory `ext-zendriver`. **Question:** how do you save the full page (not just viewport) as an artifact — and what must be configured BEFORE any download can land on disk?

## sleep-first URL refresh + empty-payload guard + download-behavior gate
**Path/Symbol:** `zendriver/core/tab.py:save_snapshot` (:1334-1349), `screenshot_b64` (:1351-1385), `save_screenshot` (:1387-1428), `print_to_pdf` (:1430-1449), `set_download_path` (:1451-1466), `download_file` (:1273-1332); element twin `Element.save_screenshot` (:929-973) via `Position.to_viewport` (:1245-1248).
**Signature:** `Tab.save_snapshot(filename="snapshot.mhtml")`; `Tab.screenshot_b64(format="jpeg", full_page=False) -> str`; `Tab.save_screenshot(filename="auto", format="jpeg") -> str` (returns saved path); `Tab.print_to_pdf(filename, **kwargs) -> pathlib.Path` (raises ValueError if filename IS a directory); `Tab.set_download_path(path)` — REQUIRED before any download works.
**Data Shape:** MHTML = single `page.capture_snapshot()` string written as text; screenshot = base64 payload → `base64.b64decode` → `write_bytes`; auto filename = `{hostname}__{last_path_segment}_{%Y-%m-%d_%H-%M-%S}{.jpg|.png}`; `_download_behavior = ["allow", str(path.resolve())]`.

### Decisive source
```python
await self.sleep()  # update the target's url          ← EVERY capture starts with this
data = await self.send(cdp.page.capture_snapshot())
if not data:
    raise ProtocolException("Could not take snapshot. Most possible cause is the page has not finished loading yet.")
# full-page screenshots: capture BEYOND the viewport, not by resizing
data = await self.send(cdp.page.capture_screenshot(format_=format,
                     capture_beyond_viewport=full_page))
# element screenshot: clip to the element's own box via Position.to_viewport(scale)
cdp.page.capture_screenshot(format, clip=viewport, capture_beyond_viewport=True)
```

**Flow:** all three exporters share one skeleton: `await self.sleep()` FIRST (the Connection breathe-wait refreshes `target.url`, so auto-derived filenames reflect the page you ACTUALLY captured, not the previous navigation), then one CDP call, then an empty-payload guard that raises `ProtocolException` with the same diagnostic ("page has not finished loading yet" is THE failure mode for early captures), then decode+write. Screenshots choose between viewport (`full_page=False`) and whole-document capture via `capture_beyond_viewport=True` — never by resizing the window; element shots reuse the geometry kit's `to_viewport()` as a CLIP region. Auto filenames are built from parsed URL parts + timestamp so parallel runs don't overwrite each other. Downloads are a separate axis: Chrome drops files only after `browser.set_download_behavior("allow", download_path=...)` — `set_download_path` sends exactly that AND latches `_download_behavior`, which `DownloadExpectation.__aenter__` later reads to restore your original behavior after a deny-window; `download_file` auto-provisions `./downloads` with a warning if you forgot. `download_file` itself navigates around the download manager: fetch→blob→objectURL→anchor `.click()` inside `call_function_on` on `<body>`, revoking the object URL after 500ms.
**Invariant:** (1) refresh state BEFORE capture (`await self.sleep()`) or auto-filenames/captures race the last navigation; (2) treat EMPTY capture payloads as "page still loading" errors — retry later rather than writing zero-byte artifacts; (3) no `set_download_behavior(allow)` ⇒ silent download loss — configure it before ANY file flow (and it's what makes expect_download's deny/restore dance meaningful); (4) PDF writes go to a FILE path, never a directory (explicit ValueError).
**Probe:** REAL test pins the download-behavior half — `tests/core/test_tab.py:test_expect_download` (:369-380, exercises DownloadExpectation deny→restore over set_download_behavior). No upstream unit test drives save_snapshot/save_screenshot/print_to_pdf themselves (coverage caveat). Deterministic pins (anchored at the `zendriver/` package dir): `grep -n 'capture_snapshot' core/tab.py` → :1342; `grep -n 'capture_beyond_viewport' core/tab.py core/element.py` → :1377/:916; `grep -n '_download_behavior' core/tab.py` → :1282,:1466.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "capture_snapshot capture_screenshot print_to_pdf set_download_behavior _download_behavior", limit: 5 });
```

## Verdict
Adopt: the sleep-refresh → capture → empty-guard skeleton for all page-artifact exports, beyond-viewport for full-page shots, clip-viewports for elements, and the explicit allow-behavior download latch (with behavior restore interplay with expect_download). Adapt auto-filename grammar to your ledger conventions. Coverage: download path test-pinned (test_expect_download); capture trio source-pinned (recorded caveat).
