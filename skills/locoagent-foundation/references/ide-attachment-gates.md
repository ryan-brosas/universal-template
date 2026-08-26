<!-- capsule-v2 -->
# IDE-selection attachment gates — how do editor state and opened files enter context under permission control?

**Source:** locoagent (Claude Code CLI fork, rev `c01bb3f`); Codebase Memory `locoagent`. **Question:** main-only collectors that bridge IDE state into the conversation.

## getSelectedLinesFromIDE / getOpenedFileFromIDE / diagnostics pair
**Path/Symbol:** `getSelectedLinesFromIDE` (:1614-1644), `getOpenedFileFromIDE` (:1864-1892), `getDiagnosticAttachments` (:2854-2877), `getLSPDiagnosticAttachments` (:2879-2935).
**Signature:** selection `(ideSelection, toolUseContext) → Promise<Attachment[]>` (main-thread only); diagnostics `(toolUseContext) → Promise<Attachment[]>`.
**Data Shape:** selected_lines carries ideName/lineStart/lineEnd/content/displayPath; opened_file is filename-ONLY (content comes from nested-memory walk preceding it).

### Decisive source
```ts
if (!ideName || ideSelection?.lineStart === undefined ||
    !ideSelection.text || !ideSelection.filePath) return []
const appState = toolUseContext.getAppState()
if (isFileReadDenied(ideSelection.filePath, appState.toolPermissionContext)) return []
// getOpenedFileFromIDE: file open triggers a NESTED-MEMORY WALK first:
const nestedMemoryAttachments = await getNestedMemoryAttachmentsForFile(
  ideSelection.filePath, toolUseContext, appState)
return [...nestedMemoryAttachments,
        { type: 'opened_file_in_ide', filename: ideSelection.filePath }]
// diagnostics gate: only useful if the agent has Bash to act on them:
if (!toolUseContext.options.tools.some(t => toolMatchesName(t, BASH_TOOL_NAME))) return []
```

**Flow:** both IDE getters run MAIN-THREAD ONLY (subagents have no IDE) → selection requires ALL fields present → read-denied paths return silently → opened-file fires the four-phase nested-memory walk (see nested-memory-attachment-walk capsule) BEFORE emitting the bare filename so AGENT.md context arrives ahead of the file reference. Diagnostics come from two registries (MCP-tracked + passive LSP): gated on Bash availability ("only useful if the agent can act"), LSP variant CLEARS its registry after delivery "to prevent memory leak" and returns [] on internal error so other attachments proceed.
**Invariant:** IDE-sourced content passes the SAME permission checks as direct reads — convenience channels never bypass deny rules; actionability gating (Bash presence) keeps dead-weight diagnostics out of subagents' context; registry drains happen only after successful conversion to attachments.
**Probe:** no upstream test (coverage caveat). Deterministic probe: `grep -n "isFileReadDenied" src/utils/attachments.ts` shows all four enforcement sites.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "getSelectedLinesFromIDE getLSPDiagnosticAttachments BASH_TOOL_NAME gate", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt permission-checked IDE bridging with actionability gates; adapt to your editor channel; omit LSP plumbing. Porting trap: injecting editor selections without deny-rule checks leaks files the user explicitly blocked; delivering diagnostics to agents without execution tools is pure context waste.
