<!-- capsule-v2 -->
# PDF print pipeline — how do you render a page to PDF with Chrome-faithful headers/footers and collision-safe filenames?

**Source:** browser-use MIT `main@3c989dc`; Codebase Memory `browser-use`. **Question:** what does Page.printToPDF need around it (margins, templates, paper tables, dedupe) to produce a usable PDF?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/tools/service.py` — `_DEFAULT_PDF_HEADER_TEMPLATE` (:66), `_DEFAULT_PDF_FOOTER_TEMPLATE` (:72), `save_as_pdf` action (:1541-1655).
**Signature:** `async def save_as_pdf(params: SaveAsPdfAction, browser_session, file_system: FileSystem)`.

### Decisive source
```python
# Default header/footer mirror Chrome's own Print dialog. A font-size MUST be set
# explicitly - Chrome defaults header/footer text to 0px, so omitting it renders
# an INVISIBLE header/footer.
'<div style="font-size:9px; ..."><span class="date"></span></div>'
# Footer flex row: min-width:0 + ellipsis lets a long URL truncate while the
# page numbers (flex-shrink:0) stay put.

paper_sizes = {'letter': (8.5,11), 'legal': (8.5,14), 'a4': (8.27,11.69), 'a3': (11.69,16.54), 'tabloid': (11,17)}
if params.display_header_footer:
    pdf_params.update({
        'displayHeaderFooter': True,
        # preferCSSPageSize governs PAGE SIZE only, NOT margins - these still apply:
        'marginTop': 0.5, 'marginBottom': 0.5, 'marginLeft': 0.4, 'marginRight': 0.4,
        'headerTemplate': ..., 'footerTemplate': ...})

result = await asyncio.wait_for(cdp_client.send.Page.printToPDF(params=pdf_params,...), timeout=30.0)
pdf_bytes = base64.b64decode(result['data'])

# Duplicate filename resolution: "name (1).pdf", "(2)", ...
while (file_system.get_dir() / f'{base} ({counter}){ext}').exists(): counter += 1
```

**Flow:** unknown paper format silently falls back to letter → focused CDP session → PrintToPDF with printBackground/landscape/scale/preferCSSPageSize + conditional margin/template block when headers requested → base64 decode → filename from param or sanitized page title (`[^\w\s-]` strip, 50 chars) → extension enforcement + FileSystem.sanitize_filename + `(n)` dedupe loop → async file write → attachments list on ActionResult.
**Invariant:** explicit margins are required whenever displayHeaderFooter is true (CSS page size does not reserve header/footer room — content gets clipped otherwise); header/footer font-size must be explicit or text renders at 0px; the title fallback chain must survive `get_current_page_title` failure ('page').
**Probe:** `tests/ci/test_action_save_as_pdf.py` — registered (:97), default filename from title (:104), custom name ± extension (:128/:149), duplicate-name dedupe (:169), landscape (:197).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "browser-use", query: "save_as_pdf printToPDF _DEFAULT_PDF_HEADER_TEMPLATE paper_sizes displayHeaderFooter", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt template constants verbatim (they encode non-obvious CDP behavior) + margins-with-headers rule + dedupe naming; adapt paper table; omit attachments plumbing if your host has none.
