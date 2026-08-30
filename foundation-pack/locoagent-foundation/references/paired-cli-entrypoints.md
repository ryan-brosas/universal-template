<!-- capsule-v2 -->
# Paired subprocess modes — how does one CLI binary serve as both an MCP server and a native-messaging host without a second executable?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How are hidden argv modes dispatched before interactive boot, and how do child processes know when their parent died?

## paired-cli-entrypoints
**Path/Symbol:** `src/entrypoints/cli.tsx:72-84`, `src/utils/claudeInChrome/mcpServer.ts` (`runClaudeInChromeMcpServer` :248-275), `chromeNativeHost.ts` (`runChromeNativeHost` :59-82).
**Signature:** `process.argv[2] === '--claude-in-chrome-mcp'` → `runClaudeInChromeMcpServer()`; `'--chrome-native-host'` → `runChromeNativeHost()` — both checked at the very top of cli.tsx, before any TUI initialization.
**Data Shape:** two sibling modes spawned BY THE SAME BINARY: MCP server (spawned by other CLI instances' dynamic stdio config, or in-process) and native host (spawned by Chrome via wrapper script).

### Decisive source
```ts
if (process.argv[2] === '--claude-in-chrome-mcp') {
    const { runClaudeInChromeMcpServer } = await import('../utils/claudeInChrome/mcpServer.js')
    ...
} else if (process.argv[2] === '--chrome-native-host') {
    const { runChromeNativeHost } = await import('../utils/claudeInChrome/chromeNativeHost.js')
```
and the parent-death contract:
```ts
// Exit when parent process dies (stdin pipe closes).
// Flush analytics before exiting so final-batch events (e.g. disconnect) aren't lost.
let exiting = false
const shutdownAndExit = async (): Promise<void> => {
  if (exiting) { return }
  exiting = true
  await shutdown1PEventLogging()
  await shutdownDatadog()
  process.exit(0)
}
process.stdin.on('end', () => void shutdownAndExit())
process.stdin.on('error', () => void shutdownAndExit())
```

**Flow:** hidden modes dispatch FIRST with lazy imports (interactive bundle never loads chrome modules); the MCP server treats stdin EOF/error as "parent CLI died" → idempotent latch → flush async analytics sinks → exit 0; the native host's equivalent signal is its message reader returning null, after which it stops its socket server.
**Invariant:** a stdio child's ONLY reliable parent-liveness oracle is its own stdin; both handlers must be idempotent (`exiting` latch) because end+error can both fire; heavy mode modules stay behind dynamic imports so the main entrypoint's cold path never pays for them. The native-host wrapper exists precisely because this binary needs ARGV to select the mode while Chrome's manifest cannot pass arguments.
**Probe:** no upstream test. Deterministic pins: `grep -n "claude-in-chrome-mcp" src/entrypoints/cli.tsx` → :72; `grep -n "stdin pipe closes" src/utils/claudeInChrome/mcpServer.ts` → :256.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "runClaudeInChromeMcpServer runChromeNativeHost", limit: 10 });
```

## Verdict
Adopt same-binary hidden-mode dispatch + stdin-EOF lifecycle for spawned helper roles. Adapt mode names. Omit analytics backend details. Coverage caveat: no unit tests upstream.
