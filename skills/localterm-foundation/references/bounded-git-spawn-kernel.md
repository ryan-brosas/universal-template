<!-- capsule-v2 -->
# Bounded git spawn kernel — how do you run git from a long-lived daemon so no invocation can hang it, blow up memory, or prompt for credentials?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853`; Codebase Memory `localterm`. **Question:** What is the minimal wrapper around `spawn(git, …)` that makes every git call in a daemon time-bounded, output-capped, prompt-free, and non-rejecting?

## One promise shape for every git call
**Path/Symbol:** `packages/server/src/utils/run-git.ts:runGit` (:28–109); limits `packages/server/src/constants.ts` (:595–600: `GIT_SPAWN_TIMEOUT_MS=30_000`, `GIT_SPAWN_MAX_STDOUT_BYTES=16MB`, `GIT_SPAWN_MAX_STDERR_BYTES=1MB`).
**Signature:** `runGit(cwd: string, args: string[], options?: { maxStdoutBytes?, maxStderrBytes? }): Promise<RunGitResult>` where `RunGitResult = { exitCode: number, stdout: Buffer, stderr: string, stdoutTruncated?, stderrTruncated? }`.
**Data Shape:** NEVER rejects — spawn errors and timeouts resolve with exitCode −1 and a synthetic stderr ("git not installed", "git timed out", "git <stream> exceeded its capture limit"); truncation is reported via flags, not thrown.

### Decisive source
```ts
const GIT_ENV = {
  ...process.env,
  GIT_PAGER: "",
  GIT_TERMINAL_PROMPT: "0",
};
...
timeout = setTimeout(() => {
  child.kill("SIGKILL");
  finish(-1, "git timed out");
}, GIT_SPAWN_TIMEOUT_MS);
```
Capture-limit kill keeps the FIRST bytes up to the cap:
```ts
child.stdout.on("data", (chunk: Buffer) => {
  if (settled) return;
  const remainingBytes = maxStdoutBytes - stdoutBytes;
  if (remainingBytes > 0) {
    const captured = chunk.subarray(0, remainingBytes);
    stdoutChunks.push(captured);
    stdoutBytes += captured.length;
  }
  if (chunk.length > remainingBytes) {
    stdoutTruncated = true;
    stopForCaptureLimit();   // SIGKILL + finish(-1, `git ${streamName} exceeded its capture limit`)
  }
});
child.on("error", () => finish(-1, "git not installed"));
child.on("close", (code) => finish(code ?? -1));
```

**Flow:** spawn resolved binary (see pi-binary-resolution-ladder's sibling `resolve-git-binary`) in caller cwd → stream handlers accumulate capped chunks with a single-shot `finish` guard (`settled` latch so timeout/error/close can't double-resolve) → SIGKILL on the 30 s ceiling or on crossing a capture cap → close resolves the normal shape; every worktree/diff/watcher call site shares this one kernel.
**Invariant:** The daemon's event loop can never be held by a hung git (pathological repo, or a credential prompt that `GIT_TERMINAL_PROMPT=0` didn't suppress gets killed at the deadline); one result shape lets callers do plain `exitCode !== 0` checks with stderr already trimmed-ready. Partial capture up to the cap is preserved on truncation rather than discarded.
**Probe:** No dedicated upstream suite names runGit directly — coverage caveat recorded honestly; its behavior is pinned transitively by every executed suite this pass (`git-worktrees` 13, `worktree-sweep` 6, `worktree-config-store` 3, `worktree-delete-pty-guard` 3 all spawn through it), plus constants pinned at constants.ts:598–600.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", query: "runGit git spawn timeout", limit: 10 });
```
Executed live pre-write: whole file read from disk (:1–109) after graph identification of `runGit` callers across git-worktrees/worktree-sweep/copy-worktree-includes; `GIT_SPAWN_*` constants confirmed at constants.ts :598–600 within the same read.

## Verdict
Adopt: env hardening (empty pager, zero terminal prompt), SIGKILL deadline, per-stream byte caps with kept-prefix + flag reporting, and the never-reject single-shape contract; adapt timeouts to your largest legitimate output (16 MB covers numstat+patch sweeps here); omit the binary-resolution layer if your host guarantees git on PATH. Trap: resolving the promise only on `close` — an `error` event (git absent) would otherwise leave the awaiter hanging forever; and forgetting that `close` can deliver a null code under signal death.
