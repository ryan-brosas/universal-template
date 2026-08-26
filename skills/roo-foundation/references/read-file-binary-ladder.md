<!-- capsule-v2 -->
# read_file binary ladder — what happens when the model points read_file at an image, a PDF, or a .exe?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** How are binary files classified, budgeted, and surfaced without ever leaking raw bytes into the transcript?

## handleBinaryFile — three-way format ladder with cumulative image budget
**Path/Symbol:** `src/core/tools/ReadFileTool.ts:handleBinaryFile` (335–422); helpers `src/core/tools/helpers/imageHelpers.ts` (whole file); extractors `src/integrations/misc/extract-text.ts:SUPPORTED_BINARY_FORMATS` (40–44).
**Signature:** `private async handleBinaryFile(task, relPath, fullPath, supportsImages, maxImageFileSize, maxTotalImageSize, imageMemoryTracker: ImageMemoryTracker, updateFileResult)`.
**Data Shape:** `ImageValidationResult {isValid, reason?: "size_limit"|"memory_limit"|"unsupported_model", notice?, sizeInMB?}`; `ImageProcessingResult {dataUrl, buffer, sizeInKB, sizeInMB, notice}`; supported binary formats = keys of `{".pdf",".docx",".ipynb",".xlsx"}` extractors.

### Decisive source
```ts
const validationResult = await validateImageForProcessing(
    fullPath, supportsImages, maxImageFileSize, maxTotalImageSize,
    imageMemoryTracker.getTotalMemoryUsed(),
)
if (!validationResult.isValid) {
    await task.fileContextTracker.trackFileContext(relPath, "read_tool")
    updateFileResult(relPath, { nativeContent: `File: ${relPath}\nNote: ${validationResult.notice}` })
    return
}
const imageResult = await processImageFile(fullPath)
imageMemoryTracker.addMemoryUsage(imageResult.sizeInMB)
```

**Flow:** extension → image? validate→process→dataUrl+notice : supported-binary? `extractTextFromFile(fullPath)` → real `addLineNumbers(content)` → `File: path\nLines 1-N:\n<numbered>` : else notice-only `Binary file (ext) - content not displayed`. Defaults 5MB per file / 20MB cumulative per READ (`ImageMemoryTracker` constructed fresh in executeNew Phase 3). Validation order: unsupported_model → per-file size_limit → cumulative memory_limit.
**Invariant:** (1) A SKIPPED image still calls `trackFileContext("read_tool")` — the read is recorded even though content is withheld; staleness tracking must not depend on visible content. (2) The memory check is `current + candidate > cap` BEFORE processing; addMemoryUsage happens only after success, so failed reads don't consume budget. (3) Images ride OUT of band: `nativeContent` gets a text note while `imageDataUrl` is attached later by buildAndPushResult only when `modelInfo.supportsImages` — never inline base64 in the text channel. (4) REAL addLineNumbers semantics differ from every mock: empty content returns `""` only when startLine===1 else `"${startLine} | \n"`; trailing newline's empty last line is popped; numbers padStart to the last number's width; result ends with `\n` (extract-text.ts:136–159). (5) LEGACY divergence: executeLegacy passes `0` as currentTotalMemoryUsed (no cross-file budget) and pushes only `[Image file - content processed for vision model]` text — dataUrl dropped on that path.
**Probe:** runner BLOCKED. Direct spec exists at tool level but MOCKS these helpers (`src/core/tools/__tests__/readFileTool.spec.ts:63–73`): image-skip reasons unsupported_model/size_limit/memory_limit each asserted via notice strings (342–393), PDF/DOCX extraction + unsupported `.exe` (412–464). Deterministic source pins: `grep -cF 'reason?: "size_limit" | "memory_limit" | "unsupported_model"' src/core/tools/helpers/imageHelpers.ts` → 1; `grep -c '".ipynb": extractTextFromIPYNB' src/integrations/misc/extract-text.ts` → 1.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", qn_pattern: ".*imageHelpers.*", fields: ["lines"], format: "json", limit: 20 });
await mcp.codebase_memory.trace_path({ project: "Roo-Code", function_name: "Roo-Code.src.core.tools.ReadFileTool.ReadFileTool.handleBinaryFile", direction: "inbound" });
```

## Verdict
Adopt the three-way ladder, the pre-check/add-after-success memory budget, and out-of-band image attachment gated on model capability. Adapt format lists and size caps. Omit the legacy path's zero-budget behavior (keep it only if you must replay old transcripts). Caveats: imageHelpers has no dedicated spec at pin — pinned via tool spec mocks + source greps; the real addLineNumbers trailing-newline behavior is source-visible only.
