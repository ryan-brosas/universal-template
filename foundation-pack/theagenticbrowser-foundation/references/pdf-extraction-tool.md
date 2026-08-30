<!-- capsule-v2 -->
# PDF extraction skill — how do you fetch a remote binary, mine its text, and never leave the temp file behind?

**Source:** TheAgenticBrowser (TheAgentic Community License 1.0) `main@71daa28`; Codebase Memory `mnt-hdd-utopia-inspo-TheAgenticBrowser`. **Question:** What is the correct async shape for a download→parse→cleanup tool that returns errors as data?

## httpx download → pdfplumber page-walk → finally-cleanup
**Path/Symbol:** `core/skills/pdf_text_extractor.py`:`extract_text_from_pdf` (`:13-49`), `download_pdf` (`:67-89`), `cleanup_temp_files` (`:51-65`).
**Signature:** `async def extract_text_from_pdf(pdf_url: str) -> str`.
**Data Shape:** Returns `"Text found in the PDF:\n" + <pages joined by \n>` or an error string; fixed download path `<root>/temp/downloaded_file.pdf`; word count computed but unused (dead local).

### Decisive source
```python
async with httpx.AsyncClient() as client:
    response = await client.get(pdf_url)
    response.raise_for_status()
with open(file_path, 'wb') as pdf_file:
    pdf_file.write(response.content)
...
with pdfplumber.open(download_result) as pdf:
    for page in pdf.pages:
        page_text = page.extract_text()
        if page_text: text += page_text + "\n"
...
finally:
    cleanup_temp_files(file_path)     # os.remove guarded by exists + try
```
**Flow:** download (async) → existence check doubles as error signal → sync pdfplumber parse → strip + prefix → return; ANY exception path still removes the file.
**Invariant:** The finally-cleanup is unconditional — an abandoned multi-MB PDF in `temp/` would otherwise accumulate per tool call. Errors are returned strings (HTTP-status errors and parse errors both), consistent with the repo's error-as-data tool contract so the critique loop can reason about them. Note the porting trap: the existence check (`if not os.path.exists(download_result): return ...`) relies on download_pdf returning either a path OR an error message — a stringly-typed union that works only because both branches return str.
**Probe:** No tests (coverage caveat). Graph pin: BA tool wrapper `extract_text_from_pdf_tool` (`browser_agent.py:302-307`) is the sole caller.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-TheAgenticBrowser", query: "pdf extract httpx plumber", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt the async-download/sync-parse/finally-cleanup trio for any document-fetching tool. Adapt parser choice (pypdf/mupdf). Omit the stringly-typed path-or-error return — use exceptions internally and stringify at the boundary.
