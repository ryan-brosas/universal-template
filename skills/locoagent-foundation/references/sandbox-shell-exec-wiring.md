<!-- capsule-v2 -->
# Sandboxed shell exec wiring — PowerShell-in-sandbox shell substitution, 0700 tmpdir, O_NOFOLLOW output, and post-command cleanup ordering

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How does the generic shell executor change when a command will run inside the sandbox — and why does sandboxed PowerShell swap its shell to /bin/sh?

## Exec-path sandbox integration
**Path/Symbol:** `src/utils/Shell.ts` : `exec` (:180-420) — sandbox branch :256-274 (wrap + tmpdir), `isSandboxedPowerShell` :256-257/:275-276, output-handle O_NOFOLLOW open :296-312, spawn env :315-340, cleanup hook :392.
**Signature:** `exec(command, abortSignal, shellType, options?: { timeout?, shouldUseSandbox?, preventCwdChanges?, ... })`.
**Data Shape:** `sandboxTmpDir = posixJoin(CLAUDE_CODE_TMPDIR || '/tmp', getClaudeTempDirName())` passed to provider only when sandboxed; output file flags numeric on POSIX (`O_WRONLY|O_CREAT|O_APPEND|O_NOFOLLOW`), string `'w'` on win32.

### Decisive source
```ts
// Sandboxed PowerShell: wrapWithSandbox hardcodes `<binShell> -c '<cmd>'` —
// using pwsh there would lose -NoProfile -NonInteractive (profile load
// inside sandbox → delays, stray output, may hang on prompts). Instead:
//   • powershellProvider.buildExecCommand (useSandbox) pre-wraps as
//     `pwsh -NoProfile -NonInteractive -EncodedCommand <base64>` — base64
//     survives the runtime's shellquote.quote() layer
//   • pass /bin/sh as the sandbox's inner shell to exec that invocation
//   • outer spawn is also /bin/sh -c to parse the runtime's POSIX output
const isSandboxedPowerShell = shouldUseSandbox && shellType === 'powershell'
const sandboxBinShell = isSandboxedPowerShell ? '/bin/sh' : binShell
```

**Flow:** When `shouldUseSandbox`: (1) provider pre-builds command with sandboxTmpDir; (2) `SandboxManager.wrapWithSandbox(commandString, sandboxBinShell)` wraps it; (3) tmpdir created with mode 0o700 (per-user name prevents multi-user permission conflicts). Output capture opens the task-output file with O_NOFOLLOW explicitly "to prevent symlink-following attacks from the sandbox" — a sandboxed process must not be able to redirect host writes through a symlink it planted. Windows needs string flags (numeric EINVAL through libuv) and grants FILE_GENERIC_WRITE because MSYS2 probes treat append-only handles as read-only. After result: `if (shouldUseSandbox) SandboxManager.cleanupAfterCommand()` runs FIRST, synchronously before any await (ghost-dotfile sweep; see bare-repo scrub capsule).

**Invariant:** (1) The sandbox's inner shell must be a shell whose quoting you control — pwsh under `<binShell> -c` loses its no-profile flags and can hang on prompts inside the fence; base64 EncodedCommand is the payload shape that survives the runtime's quote layer. (2) Every fd the sandbox can influence gets O_NOFOLLOW; every path the sandbox could plant gets deny-or-scrub; these are the same threat model at two layers. (3) Cleanup ordering (sync, before await) is load-bearing for callers awaiting `.result`.

**Probe:** anchored at the locoagent repo root — `grep -n 'isSandboxedPowerShell' src/utils/Shell.ts | head -2` → :256,:257; `grep -n 'mode: 0o700' src/utils/Shell.ts` → :269; `grep -c O_NOFOLLOW src/utils/Shell.ts` → ≥3; `grep -n 'O_NOFOLLOW prevents symlink-following' src/utils/Shell.ts` → :299.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "wrapWithSandbox sandboxed PowerShell EncodedCommand binShell", limit: 5 });
```

## Verdict
Adopt the inner-shell substitution pattern whenever your sandbox wrapper has a hardcoded `<sh -c>` contract, plus O_NOFOLLOW-on-sandbox-output and sync-first cleanup. Adapt tmpdir naming to your per-user scheme; omit the Windows append-mode saga unless you target win32. Coverage caveat: no upstream unit tests; anchors pinned line-exact.
