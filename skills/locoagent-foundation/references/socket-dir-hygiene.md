<!-- capsule-v2 -->
# Socket-dir hygiene — how do you keep per-PID Unix sockets from leaking, colliding across users, or trusting a pre-existing path?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** What is the full lifecycle contract for a `/tmp` socket directory shared by many short-lived CLI sessions?

## socket-dir-hygiene
**Path/Symbol:** `src/utils/claudeInChrome/common.ts` (`getSocketDir` :474-476, `getSecureSocketPath` :481-486, `getAllSocketPaths` :492-527, `getUsername` :534-540) + `chromeNativeHost.ts:start()` :117-163.
**Signature:** `getSocketDir(): string` → `` `/tmp/claude-mcp-browser-bridge-${username}` ``; `getSecureSocketPath(): string` → `<dir>/<process.pid>.sock`, or on win32 the named pipe `\\.\pipe\claude-mcp-browser-bridge-<user>`; `getAllSocketPaths(): string[]` → live dir scan ∪ legacy fallbacks.
**Data Shape:** username resolved via `userInfo().username || 'default'`, falling back to `process.env.USER || USERNAME || 'default'` when userInfo throws.

### Decisive source
```ts
// Migrate legacy socket: if socket dir path exists as a file/socket, remove it
const dirStats = await stat(socketDir)
if (!dirStats.isDirectory()) {
  await unlink(socketDir)
}
// Create socket directory with secure permissions
await mkdir(socketDir, { recursive: true, mode: 0o700 })
await chmod(socketDir, 0o700).catch(() => {})
```
and stale-socket reaping:
```ts
const pid = parseInt(file.replace('.sock', ''), 10)
if (isNaN(pid)) continue
try {
  process.kill(pid, 0)      // Process is alive, leave it
} catch {
  await unlink(join(socketDir, file))  // Process is dead, remove stale socket
}
```

**Flow:** every startup: (1) if the dir path exists but is NOT a directory, unlink it (legacy installs left a plain socket/file there); (2) mkdir mode 0o700 + unconditional chmod 0o700 (fixes a pre-existing too-open dir); (3) reap sockets whose encoded PID fails `kill(pid, 0)`; (4) listen, then chmod the SOCKET file itself to 0600 — after listen resolves, because the file only exists then. Discovery (`getAllSocketPaths`) scans for `*.sock` and appends two LEGACY fallback paths (tmpdir-relative and absolute `/tmp/...` under the old non-PID name) so old extension builds still find a bridge.
**Invariant:** the username segment is load-bearing — without it, `/tmp/claude-mcp-browser-bridge` is a cross-user collision/hijack point; PID-liveness (`kill(pid,0)`) is the ONLY staleness oracle (mtime heuristics kill live bridges); socket-file chmod must happen post-listen. Windows uses named pipes so all dir logic is gated on `platform() !== 'win32'`.
**Probe:** no upstream test. Deterministic pins: `grep -n "mode: 0o700\|chmod" src/utils/claudeInChrome/chromeNativeHost.ts` → :131/:134/:185; `grep -n "kill(pid, 0)" src/utils/claudeInChrome/chromeNativeHost.ts` → :150.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "getSecureSocketPath getAllSocketPaths", limit: 10 });
```

## Verdict
Adopt the four-step startup hygiene sequence and PID-encoded naming. Adapt pipe names/dir roots per OS. Omit the ant-only logging. Coverage caveat: no unit tests upstream.
