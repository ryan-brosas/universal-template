<!-- capsule-v2 -->
# Execution-time tool gate — which checks run at CALL time that filtering alone cannot catch?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** Tools were already filtered for the mode when the request was built — why does execution re-validate, and what does it add?

## validateToolUse + isToolAllowedForMode: alias resolution, requirement precedence, param-aware file restrictions
**Path/Symbol:** `src/core/tools/validateToolUse.ts` (`isValidToolName` :14-30, `validateToolUse` :32-63, `isToolAllowedForMode` :120-239); patch-path extraction :79-104.
**Signature:** `isToolAllowedForMode(tool, modeSlug, customModes, toolRequirements?, toolParams?, experiments?, includedTools?): boolean` (throws `FileRestrictionError` on edit-group violations); `validateToolUse(...)` converts both failure modes to thrown Errors with model-facing text.
**Data Shape:** Precedence inputs: `TOOL_ALIASES` (alias→canonical), `toolRequirements` record (disabledTools), `ALWAYS_AVAILABLE_TOOLS`, `EXPERIMENT_IDS`, per-mode group entries possibly `[groupName, {fileRegex, description}]`, `EDIT_OPERATION_PARAMS` list used to detect real edit payloads vs streaming path-only probes.

### Decisive source
```ts
const resolvedTool = TOOL_ALIASES[tool] ?? tool
if (toolRequirements && (tool in toolRequirements && !toolRequirements[tool] ||
    resolvedTool in toolRequirements && !toolRequirements[resolvedTool])) return false
if (ALWAYS_AVAILABLE_TOOLS.includes(tool)) return true          // AFTER explicit disable
...
if (groupName === "edit" && options.fileRegex) {
  const filePath = toolParams?.path || toolParams?.file_path
  const isEditOperation = EDIT_OPERATION_PARAMS.some(param => toolParams?.[param])
  if (filePath && isEditOperation && !doesFileMatchRegex(filePath, options.fileRegex))
    throw new FileRestrictionError(mode.name, options.fileRegex, options.description, filePath, tool)
  if (tool === "apply_patch") // extract *** Add/Delete/Update File: paths from patch text, test EACH
}
```

**Flow:** existence check (static names ∪ experiment-gated custom registry ∪ dynamic `mcp_*`) → alias resolution → requirements veto → always-available escape → custom-tool pass → experiment toggle check → mode lookup → group scan where dynamic MCP tools ride the `mcp` group and edit-group fileRegex is enforced against ACTUAL params (multi-file patches validated per-file). Invalid regex patterns log-and-mismatch (fail-closed for the restriction).
**Invariant:** Explicit disable beats ALWAYS_AVAILABLE (documented ordering guarantee shared with the filtering layer — filter-tools-for-mode); file restrictions evaluate only genuine operations so streaming path-only calls don't false-trip; unknown tools get an actionable tool-list error, not a silent deny.
**Probe:** `src/core/tools/__tests__/validateToolUse.spec.ts` ("prioritizes requirements over ALWAYS_AVAILABLE_TOOLS" :163, dynamic-MCP matrix :102-137).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "isToolAllowedForMode FileRestrictionError TOOL_ALIASES", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt two-layer authorization: build-time filtering decides WHAT THE MODEL SEES, this call-time gate enforces WHAT CAN RUN (params included). Adapt group vocabulary; keep the precedence order (requirements > always-available > experiments > groups). Omit VS Code error-toast plumbing around FileRestrictionError.
