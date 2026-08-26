<!-- capsule-v2 -->
# read_file approval keys — how does ONE ask message carry per-file permissions for a multi-file read?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** What is the exact approval-message grammar that lets the UI approve/deny individual files inside one read_file ask, and what happens when the reply cannot be parsed?

## requestApproval — single vs batch with key-matched JSON permissions
**Path/Symbol:** `src/core/tools/ReadFileTool.ts:requestApproval` (427–534), key builders `getLineSnippet` (551–567) / `getStartLine` (539–546), result assembly `buildAndPushResult` (572–621).
**Signature:** `private async requestApproval(task, filesToApprove: FileResult[], updateFileResult: (path, updates: Partial<FileResult>) => void)`.
**Data Shape:** batch ask payload `{tool:"readFile", batchFiles:[{path, lineSnippet, isOutsideWorkspace, key, content}]}` where `key = \`${readablePath}${lineSnippet ? \` (${lineSnippet})\` : ""}\``; UI replies yes/no OR free-text JSON map `{[key]: boolean}`.

### Decisive source
```ts
} else {
    // Individual permissions
    try {
        const individualPermissions = JSON.parse(text || "{}")
        let hasAnyDenial = false
        batchFiles.forEach((batchFile, index) => {
            const fileResult = filesToApprove[index]
            const approved = individualPermissions[batchFile.key] === true
            if (approved) { updateFileResult(fileResult.path, { status: "approved" }) }
            else {
                hasAnyDenial = true
                updateFileResult(fileResult.path, {
                    status: "denied",
                    nativeContent: `File: ${fileResult.path}\nStatus: Denied by user`,
                })
            }
        })
        if (hasAnyDenial) task.didRejectTool = true
    } catch {
        task.didRejectTool = true
        filesToApprove.forEach((fr) => {
            updateFileResult(fr.path, { status: "denied", nativeContent: `File: ${fr.path}\nStatus: Denied by user` })
        })
    }
}
```

**Flow:** >1 pending files → batch ask keyed by readablePath+lineSnippet; response routing: `yesButtonClicked` → all approved (+feedback attached to every FileResult); `noButtonClicked` → all denied + `task.didRejectTool=true`; anything else → parse text as per-key JSON. Single file → one ask carrying `reason`/`startLine`, anything ≠ yesButtonClicked denies. buildAndPushResult then joins every non-empty nativeContent with `\n\n---\n\n` and picks ONE status banner by precedence denied-with-feedback > didRejectTool > approved-with-feedback.
**Invariant:** (1) Permission matching is EXACT STRING on the composed key — any host change to getReadablePath/getLineSnippet formatting silently breaks the round-trip and denies everything. (2) Unparseable or missing permission maps fail CLOSED: every file denied + didRejectTool set (no partial state from garbage). (3) Approval is requested BEFORE any fs access in executeNew (Phase 2 precedes Phase 3) — denied files never touch disk. (4) lineSnippet always renders the limit (`(up to N lines)` even at default) so the user can judge exposure; slice ranges only shown when offset>1; indentation mode always shows its effective anchor. (5) Feedback text/images propagate into FileResults and are re-emitted via formatResponse.toolDeniedWithFeedback/toolApprovedWithFeedback, images stripped unless the final model supportsImages.
**Probe:** runner BLOCKED. Direct spec pins single-file paths: `src/core/tools/__tests__/readFileTool.spec.ts:584–648` (yes→no rejection sets didRejectTool; feedback re-emitted via say("user_feedback") and toolDeniedWithFeedback). Deterministic source pins from repo root: `grep -cF 'individualPermissions[batchFile.key] === true' src/core/tools/ReadFileTool.ts` → 1; `grep -cF 'Status: Denied by user' src/core/tools/ReadFileTool.ts` → 5 (batch ×3, single ×1, legacy loop ×1 — the same denial shape on every path); `grep -cF '(up to ${limit} lines)' src/core/tools/ReadFileTool.ts` → 1.
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "Roo-Code", qualified_name: "Roo-Code.src.core.tools.ReadFileTool.ReadFileTool.requestApproval" });
```

## Verdict
Adopt key-matched per-item approval JSON with fail-closed parse handling for ANY multi-target tool ask; adopt the pre-disk approval ordering. Adapt the key grammar to your UI but version it if it can ever change. Omit the legacy path's inline per-file asks (executeLegacy re-asks inside the loop — kept only for old-transcript compatibility). Caveat: the batch/individual-permissions branch has no direct spec at pin — pinned via source read + greps; spec covers single-file flow only.
