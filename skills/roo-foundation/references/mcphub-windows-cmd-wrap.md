<!-- capsule-v2 -->
# Windows cmd.exe command wrapping — how do you run .ps1-implemented commands (npx from fnm/nvm-windows/volta) as MCP stdio servers without double-wrapping users who already wrapped?

**Source:** Roo-Code (Roo Code, Inc.) Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** On Windows, how do you make `command: "npx"` work when node version managers ship it as a PowerShell script, and when must you NOT re-wrap?

## Wrap every stdio command in cmd /c unless it is already cmd
**Path/Symbol:** `src/services/mcp/McpHub.ts` (stdio arm of `connectToServer` :707–721).
**Signature:** `const isAlreadyWrapped = configInjected.command.toLowerCase() === "cmd.exe" || configInjected.command.toLowerCase() === "cmd"`.
**Data Shape:** applies to the INJECTED config (`injectVariables` output) at transport-construction time; non-Windows platforms are untouched (`process.platform === "win32"` gate).

### Decisive source
```ts
// :706-721
const isWindows = process.platform === "win32"
// Check if command is already cmd.exe to avoid double-wrapping
const isAlreadyWrapped =
    configInjected.command.toLowerCase() === "cmd.exe" || configInjected.command.toLowerCase() === "cmd"
const command = isWindows && !isAlreadyWrapped ? "cmd.exe" : configInjected.command
const args =
    isWindows && !isAlreadyWrapped
        ? ["/c", configInjected.command, ...(configInjected.args || [])]
        : configInjected.args
```

**Flow:** on win32 every user command becomes `cmd.exe /c <userCommand> <args…>`; a user command that IS `cmd`/`CMD`/`cmd.exe` (case-insensitive) passes through untouched with its own args. Comment records WHY: node version managers implement commands as PowerShell scripts, which only resolve through an extra shell layer.
**Invariant:** wrap exactly once — the check compares lowercased against BOTH `"cmd.exe"` and `"cmd"`, so an already-wrapped `["/c", …]` args array must never get a second `/c` prefix. Cost acknowledged in source: one extra shell hop per server start.
**Probe:** `src/services/mcp/__tests__/McpHub.spec.ts` describe `"Windows command wrapping"`: it `"should wrap commands with cmd.exe on Windows"` (:2045), `"should not wrap commands that are already cmd.exe"` (:2167), `"should handle npx.ps1 scenario from node version managers"` (:2229), `"should handle case-insensitive cmd command check"` (:2309 — asserts `StdioClientTransport` received `command: "CMD"`, `args: ["/c","echo","test"]` unchanged).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "Windows cmd.exe wrap npx.ps1 StdioClientTransport", limit: 5 });
// same Method row as connectToServer 655-896 (single containing symbol; BM25 ranks the wrapper tests' describe block nearby)
```

## Verdict
Adopt the wrap-once ladder including the lowercase double-name check. Adapt the wrapper binary per host shell (pwsh/bash need no such shim). Omit nothing — the double-wrap guard is the whole point.
