<!-- capsule-v2 -->
# Read pipeline extraction ladder — how does one reader serve PDF/DOCX/XLSX/PPTX and mislabeled legacy files?

**Source:** mike AGPL-3.0 `main@3ad9a5ff`; Codebase Memory `ext-mike`. **Question:** What extraction order guarantees the model reads text that matches what edit_document can anchor against, across every supported file type?

## Version-aware byte resolution + per-type extractor chain + sentinel returns
**Path/Symbol:** `backend/src/lib/chat/tools/documentOps.ts:1448` (`readDocumentContent`), `:1120` (`loadCurrentVersionBytes`), `:57` (`extractPdfText`); spreadsheet/presentation helpers in `src/lib/spreadsheet.ts` + `officeText.ts`; magic-byte dev logging at :1554-1565. Direct tests: `src/lib/__tests__/documentGeneration.test.ts`, `documentVersions.test.ts`.
**Signature:** `readDocumentContent(docLabel, docStore, write, docIndex?, db?, {emitEvents?, readIdentity?}?) -> Promise<string>`; failure sentinels `"Document not found."` / `"Document could not be read."` (consumers — verifyCitations UNREADABLE_SOURCES — match these EXACT strings).
**Data Shape:** bytes resolved current-version-first (tracked-changes view) then original storage_path fallback; emitEvents=false mode suppresses SSE lifecycle events for internal reads (find_in_document reuse, citation verification).

### Decisive source
```ts
if (fileType === "docx") {
    // Use the same flattening as the edit_document matcher so the LLM sees
    // exactly the characters it can anchor against.
    text = await extractDocxBodyText(Buffer.from(raw));
    if (!text) { /* mammoth extractRawText fallback */ }
} else if (isSpreadsheetDocumentType(fileType)) {
    text = spreadsheetToLLMText(…);   // cell-addressed markdown w/ Excel-formatted values
} else if (legacy Office) { … docxToPdf → extractPdfText … }
else { … mammoth try … }              // unknown types: best-effort mammoth, never throw
```

**Flow:** doc_read_start/doc_read SSE pairs bracket the work (unless suppressed) → inline_text fast path for request-scoped Word bodies → version-resolved bytes → per-type extraction → ALWAYS return a string (sentinels on failure), never throw past the catch which still emits the closing doc_read event.
**Invariant:** The read/edit character contract: docx text comes from the SAME flattener the edit matcher uses, so find/context anchors the model quotes are guaranteed to exist in the editable document. Extraction failures degrade to sentinel strings that downstream verification treats as no-source rather than false-negative matching against error prose. Legacy .doc/.ppt ride a PDF conversion detour; truncated/mislabeled uploads are identified by first-8-byte magic logging (PK\x03\x04 vs OLE vs %PDF).
**Probe:** `grep -c 'extractDocxBodyText' src/lib/chat/tools/documentOps.ts | head -1` ≥ 3; `grep -c 'Document could not be read.' src/lib/chat/tools/documentOps.ts` → 4 (return + comment + test-facing sentinel reuse);

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-mike", query: "readDocumentContent loadCurrentVersionBytes extractPdfText", limit: 10 });
```

## Verdict
Adopt sentinel-returning readers + read/edit character-contract alignment + version-first byte resolution; adapt your extractor set; omit pdf.js/mammoth specifics.
