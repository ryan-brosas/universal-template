<!-- capsule-v2 -->
# PS execution provider — how does a PowerShell command travel through sandbox wrappers, cwd tracking, and exit-code capture without being corrupted by quoting layers?

**Source:** LocoAgent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** How is the exec command string assembled for PowerShell under both direct spawn and the sandbox runtime's mandatory `sh -c` wrapping?

## EncodedCommand as quoting-proof envelope + $LASTEXITCODE-first exit capture
**Path/Symbol:** `src/utils/shell/powershellProvider.ts`:`buildPowerShellArgs` (:11-13), `encodePowerShellCommand` (:23-25), `buildExecCommand` (:35-97), `getEnvironmentOverrides` (:103-121); consumer `sandbox-shell-exec-wiring.md` (pass-23) documents the same swap from the sandbox side.
**Signature:** `function createPowerShellProvider(shellPath: string): ShellProvider` with `buildExecCommand(command, { id, sandboxTmpDir, useSandbox }): Promise<{ commandString; cwdFilePath }>`.
**Data Shape:** Non-sandbox: bare PS command + flags via getSpawnArgs (`-NoProfile -NonInteractive -Command`). Sandbox: `'pwsh' -NoProfile -NonInteractive -EncodedCommand <base64>` joined as ONE string for `/bin/sh -c`.

### Decisive source
```ts
// -EncodedCommand (base64 UTF-16LE), not -Command: the sandbox runtime
// applies its OWN shellquote.quote() on top of whatever we build. Any
// string containing ' triggers double-quote mode which escapes ! as \\! —
// POSIX sh preserves that literally, pwsh parse error. Base64 is
// [A-Za-z0-9+/=] — no chars that any quoting layer can corrupt.
const commandString = opts.useSandbox
  ? [`'${shellPath.replace(/'/g, `'\\\\''`)}'`, '-NoProfile', '-NonInteractive', '-EncodedCommand', encodePowerShellCommand(psCommand)].join(' ')
  : psCommand
```

**Flow:** append cwd-tracking epilogue to the user command: exit code prefers `$LASTEXITCODE` (native exe truth) falling back to `$?` only when no native ran — because PS 5.1 sets `$? = $false` when a native command writes stderr under `2>&1` even on exit 0 → write `(Get-Location).Path` to a per-id file (`-Encoding utf8 -NoNewline`) → `exit $_ec`. The cwd FILE lives in sandboxTmpDir (not tmpdir()) when sandboxed since only that dir is writable. Session env vars apply first so sandbox TMPDIR cannot be overridden.
**Invariant:** The base64 envelope is quoting-inert across EVERY wrapper layer — never replace it with escaped strings when an outer quoter exists. `$LASTEXITCODE`-preference trades two rare misclassifications (mixed native/cmdlet compounds) for eliminating the common false-failure class.
**Probe:** `grep -nF "if ($null -ne $LASTEXITCODE)" src/utils/shell/powershellProvider.ts` and `grep -nF "claude-pwd-ps-" src/utils/shell/powershellProvider.ts` (anchored at the locoagent repo root).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "createPowerShellProvider buildExecCommand EncodedCommand", limit: 10, fields: ["signature", "name", "file"] });
```
*(resolves parser-side toUtf16LeBase64 twin and Shell provider consumers)*

## Verdict
Adopt the encoding-envelope principle and LASTEXITCODE-first capture. Adapt flag sets and env-ordering policy. Omit bash-provider comparison notes. Coverage caveat: probes deterministic; no upstream tests.
