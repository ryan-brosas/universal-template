<!-- capsule-v2 -->
# Codex CLI-shim host tools — how do you expose host tools to a runtime whose only execution surface is a bash tool?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** When the sandboxed agent runtime has no MCP or native tool-callback surface, how do host-provided tools become callable by the model without inventing a new transport?

## Prompt-framed CLI shim, applied once per session
**Path/Symbol:** `packages/harness-codex/src/codex-harness.ts` — `composeToolUsageInstructions` (:1213–1251), `frameInitialPromptGuidance` (:1200–1211), `initialPromptGuidanceApplied` seed (:711–717), application site in doPromptTurn (:908–921), shim path construction (:299–300) and `--cli-shim-dir` spawn arg (:444); shim file constant imported from `./bridge/cli-relay` (`CLI_SHIM_FILENAME`, :61).
**Signature:** `composeToolUsageInstructions({tools, cliShimPath}): string`; `frameInitialPromptGuidance({toolUsageBlock, userText}): string`.
**Data Shape:** `cliShimPath = <sessionDataDir>/codex/<CLI_SHIM_FILENAME>` (written into the sandbox at bootstrap); guidance = one `<host-tool-instructions>` block listing each tool's name/description/input schema plus the exact invocation line; user text wrapped in `<user-message>` tags.

### Decisive source
```ts
// codex-harness.ts:1228–1233 — the invocation contract is ONE CLI form
const lines: string[] = [
  '<host-tool-instructions>',
  'You have access to the following host-provided tools. To use one, run the following command via your built-in `bash` tool:',
  '',
  `  node ${cliShimPath} <toolName> '<jsonInput>'`,
  '',
  'The script prints the JSON result to stdout. Do not invent another way to call these tools — only this CLI invocation will work. Pass the JSON input as a single-quoted argument.',
  // ...per-tool name/description/input-schema lines...
];
// :1200–1211 — blocks + user text framed into one message
return `${blocks.join('\n\n')}\n\n<user-message>\n${userText}\n</user-message>`;
// :711–717 + :908–921 — applied ONCE per session lifetime
/*
 * Host-tool relay guidance is prepended to the first user message of a fresh
 * session only. A resumed session (attach/replay/rerun) already carried it in
 * its original first message (preserved in the persisted thread), so it
 * starts "applied".
 */
let initialPromptGuidanceApplied = isResume;
if (!initialPromptGuidanceApplied) {
  promptText = frameInitialPromptGuidance({ toolUsageBlock: /* composeToolUsageInstructions */ , userText: promptText });
}
initialPromptGuidanceApplied = true;
```

**Flow:** doStart creates `<sessionDataDir>/codex` and passes `--cli-shim-dir` to bridge.mjs (the bridge serves the shim to the agent's bash calls) → on the FIRST prompt of a fresh session, doPromptTurn composes the instructions block from the turn's tool list and frames it with the user text → latches `initialPromptGuidanceApplied = true` → every later prompt sends raw user text only; a resumed session seeds the flag TRUE because its persisted thread already contains the original framed first message.
**Invariant:** guidance is applied EXACTLY ONCE per session lifetime (fresh or resumed) — re-announcing it would duplicate system-level instructions inside an already-guided thread; the model is told there is exactly one working invocation form, so host-side correlation can key on the shim path; file/image prompt parts THROW rather than being silently dropped (`extractUserText` :1244–1262 documents the gap).
**Probe:** NO test pins the guidance framing itself (coverage caveat — deterministic read only); the dialect's capability boundaries are pinned by `codex-harness.test.ts:207–231` ("rejects built-in permission modes other than allow-all", "rejects built-in tool filtering controls") and token-reuse attach at :515–556.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "composeToolUsageInstructions frameInitialPromptGuidance cliShimPath initialPromptGuidanceApplied", limit: 10 });
```

## Verdict
Adopt prompt-framed CLI shim for runtimes with no MCP/tool-callback surface — the bash tool becomes the universal execution surface and the shim path becomes the correlation key; adapt the shim location, framing tags, and once-per-session seeding rule; omit the MCP host-tool machinery used by ACP/opencode/claude-code/deepagents (mcpServers in the start frame). Caveat: guidance content is read-only evidence, not test-pinned.
