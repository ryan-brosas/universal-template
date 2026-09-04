<!-- capsule-v2 -->
# Shell tool — bounded, cross-platform command execution

**Source:** opencode MIT `<branch>@<commit>`; Codebase Memory `opencode`. **Question:** how does a shell tool run commands safely across platforms with a timeout and env-expansion?

## Connected graph-selected seam
**Path/Symbol:** `packages/opencode/src/tool/shell.ts` (645 lines): `ShellTool` (:338), `defaultTimeoutMs` (`flags.bashDefaultTimeoutMs ?? 2*60*1000`), `auto` (:147), `expand` (:154-158), `cmd` (:293-304), `cygpath` (:349), `resolvePath` (:360+).
**Signature:** `execute({command, cwd?, timeout?}, ctx)` — spawns the shell, applies a default 2-minute timeout, expands `$HOME`/`$PWD`/`$PSHOME` env vars, resolves paths (cygpath on Windows).
**Data Shape:** `Parameters` from `shell/prompt.ts`; `cmd()` builds the shell invocation (PowerShell `-NoLogo -NoProfile -NonInteractive -Command` on win32; plain shell otherwise).

### Decisive source
```ts
const defaultTimeoutMs = flags.bashDefaultTimeoutMs ?? 2 * 60 * 1000
// env expansion: $HOME, $PWD, $PSHOME resolved to the actual shell dirs
function expand(text: string, cwd: string, shell: string) {
  return text.replace(/\$(HOME|PWD|PSHOME)(?=$|[\\/])/gi, (_, key) => auto(key, cwd, shell) || "")
}
// win32 PowerShell invocation
if (process.platform === "win32" && Shell.ps(shell)) {
  return ChildProcess.make(shell, ["-NoLogo", "-NoProfile", "-NonInteractive", "-Command", command], ...)
}
```

**Flow:** resolve the shell + cwd → expand env vars → build the invocation (platform-specific) → spawn with a default timeout → capture output (bounded). Paths resolved via cygpath on Windows for cross-platform correctness.
**Invariant:** a default 2-minute timeout bounds every command; env expansion is safe (only `$HOME`/`$PWD`/`$PSHOME`); output is bounded.
**Probe:** `packages/opencode/test/tool/shell.test.ts` (command runs and returns output; timeout bounds a long command; env expansion; cwd resolution).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "ShellTool shell command timeout expand env cwd spawn", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the bounded cross-platform shell tool with default timeout, safe env expansion, and path resolution; adapt the shell dialect and timeout to host; omit the Effect service wiring unless the target uses Effect.
