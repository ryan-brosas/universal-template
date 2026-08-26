<!-- capsule-v2 -->
# Tab-ID render hooks — how do you attach a "focus this tab" deep link to MCP tool output when the tab id lives inside arbitrary tool input?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How does the CLI know which browser tabs a session touched, and how are chrome MCP tools' names/results rendered down to one line?

## chrome-tab-render-hooks
**Path/Symbol:** `src/utils/claudeInChrome/toolRendering.tsx` (`renderChromeToolUseMessage` :17-115, `renderChromeViewTabLink` :124-142, `renderChromeToolResultMessage` :149-215, `getClaudeInChromeMCPToolOverrides` :221-258), consumer `src/services/mcp/client.ts:1977-1981`, tracking set in `common.ts` :415-427.
**Signature:** `getClaudeInChromeMCPToolOverrides(toolName): {userFacingName, renderToolUseMessage, renderToolUseTag, renderToolResultMessage}` — spread into a matched tool's rendering record.
**Data Shape:** `tabId` may arrive as number OR numeric string (parsed with `parseInt` + `isNaN` guard); 17 tool names hardcoded in `ChromeToolName` union ("Keep in sync with the package's BROWSER_TOOLS array"); tracked set capped at `MAX_TRACKED_TABS = 200`.

### Decisive source
```ts
const tabId = input.tabId;
if (typeof tabId === 'number') {
  trackClaudeInChromeTabId(tabId);
}
```
and the empty-string-not-null rule:
```ts
case 'read_page':
...
  // These tools don't have meaningful secondary info to show inline.
  // Return empty string (not null) to ensure tool header still renders.
  return '';
```
plus the blunt overflow policy:
```ts
if (trackedTabIds.size >= MAX_TRACKED_TABS && !trackedTabIds.has(tabId)) {
  trackedTabIds.clear()
}
```

**Flow:** every chrome tool-use render records its `tabId` into a module-global Set → other subsystems (e.g. attachment/permission logic) ask `isTrackedClaudeInChromeTabId()`; the tool-use TAG renders `[View Tab]` hyperlink (`https://clau.de/chrome/tab/<id>`) only when `supportsHyperlinks()`; non-verbose results collapse to a one-line summary ("Navigation completed", "Page read", ...) while verbose delegates to the default MCP renderer; display name trims the `_mcp` suffix (`tabs_create_mcp` → `Claude in Chrome[tabs_create]`).
**Invariant:** inline info must return EMPTY STRING rather than null or the tool header itself disappears — a rendering contract, not styling; the tab Set is best-effort UI state with clear-on-overflow (NOT an LRU) because it only gates convenience links; string-typed tabIds must be coerced before lookup since extension payloads drift between number and string.
**Probe:** no upstream test. Deterministic pins: `grep -n "not null" src/utils/claudeInChrome/toolRendering.tsx` → :111; `grep -n "MAX_TRACKED_TABS" src/utils/claudeInChrome/common.ts` → :415/:419.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "getClaudeInChromeMCPToolOverrides trackClaudeInChromeTabId", limit: 10 });
```

## Verdict
Adopt the overrides-spread hook shape and empty-string header rule. Adapt link URLs and tool-name unions. Omit per-tool summary prose. Coverage caveat: no unit tests upstream.
