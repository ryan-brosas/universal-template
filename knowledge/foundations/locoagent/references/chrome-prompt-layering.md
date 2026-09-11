<!-- capsule-v2 -->
# Chrome prompt layering — how do you keep a browser-automation system prompt, a ToolSearch gate, and a skill-invocation hint from being injected at the wrong times?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** Which of the four chrome instruction blocks is static, which is request-time conditional, and which steers the model AWAY from raw tools?

## chrome-prompt-layering
**Path/Symbol:** `src/utils/claudeInChrome/prompt.ts` (`BASE_CHROME_PROMPT` :1-46, `CHROME_TOOL_SEARCH_INSTRUCTIONS` :53-61, `CLAUDE_IN_CHROME_SKILL_HINT` :76, `CLAUDE_IN_CHROME_SKILL_HINT_WITH_WEBBROWSER` :83), consumers `src/services/api/claude.ts:1367`, `src/utils/attachments.ts:1560-1583`, `src/main.tsx:1571`.
**Signature:** `getChromeSystemPrompt(): string` returns ONLY `BASE_CHROME_PROMPT` — deliberately without tool-search text.
**Data Shape:** four constants: (1) base prompt — GIF capture rules, console-pattern filtering, NEVER trigger JS alert/confirm dialogs (they block the extension's event loop), rabbit-hole stop rules (2-3 failed attempts ⇒ ask user), call `tabs_context_mcp` FIRST at session start and never reuse tab ids across sessions; (2) ToolSearch instructions; (3)/(4) startup hints with/without a competing WebBrowser tool.

### Decisive source
```ts
/**
 * Get the base chrome system prompt (without tool search instructions).
 * Tool search instructions are injected separately at request time in claude.ts
 * based on the actual tool search enabled state.
 */
export function getChromeSystemPrompt(): string {
  return BASE_CHROME_PROMPT
}
```
and the delta-attachment synthesis in attachments.ts:
```ts
// The chrome ToolSearch hint is client-authored and ToolSearch-conditional;
// actual server `instructions` are unconditional. Decide the chrome part
// here, pass it into the pure diff as a synthesized entry.
clientSide.push({
  serverName: CLAUDE_IN_CHROME_MCP_SERVER_NAME,
  block: CHROME_TOOL_SEARCH_INSTRUCTIONS,
})
```

**Flow:** base prompt rides setup (`setupClaudeInChrome().systemPrompt`); ToolSearch instructions are appended at REQUEST time only when tool search is actually enabled (`isToolSearchEnabledOptimistic() && modelSupportsToolReference(model) && isToolSearchToolAvailable(tools)`) and enter as an mcp-instructions-delta attachment keyed to the server name; at STARTUP main.tsx injects the skill hint (WebBrowser-aware variant when Bun+WebView exists) telling the model to invoke the `claude-in-chrome` SKILL before touching any `mcp__claude-in-chrome__*` tool.
**Invariant:** prompt layers have different lifetimes and must not be merged: session-static guidance belongs in the system prompt; tool-loading gates are per-request because tool availability changes mid-session; the skill hint exists precisely so tools arrive DISABLED until instructions load. The alert-dialog prohibition is safety-of-session (a blocked extension looks identical to a hung browser).
**Probe:** no upstream test. Deterministic pins: `grep -n "without tool search instructions" src/utils/claudeInChrome/prompt.ts` → :64; `grep -n "injectChromeHere" src/services/api/claude.ts` → :1366-1367 region; `grep -n "CLAUDE_IN_CHROME_SKILL_HINT" src/main.tsx` → :1571.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "BASE_CHROME_PROMPT CHROME_TOOL_SEARCH_INSTRUCTIONS", limit: 10 });
```

## Verdict
Adopt the three-layer split (static / request-conditional / startup-hint) and its injection points. Adapt prompt prose. Omit ant-only wording. Coverage caveat: no unit tests upstream.
