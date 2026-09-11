<!-- capsule-v2 -->
# pi.exe / pi.cmd — Windows .cmd spawn needs shell:true, POSIX never does

**Source:** pi-acp-jetbrain MIT `main@27aac05f`; Codebase Memory `pi-acp`. **Question:** How do you spawn a globally-installed npm CLI (`pi`) portably when Windows wraps it in a `.cmd` shim that Node refuses to execute without a shell?

## Command resolution
**Path/Symbol:** `src/pi-rpc/command.ts` whole file (16L): `defaultPiCommand` (:3-5), `getPiCommand` (:7-9), `shouldUseShellForPiCommand` (:11-16). Consumed in `src/pi-rpc/process.ts:140,156`.
**Signature:** `getPiCommand(override?: string): string`; `shouldUseShellForPiCommand(cmd: string): boolean`.

### Decisive source
```ts
export function defaultPiCommand(): string {
  return platform() === 'win32' ? 'pi.cmd' : 'pi'
}
export function shouldUseShellForPiCommand(cmd: string): boolean {
  if (platform() !== 'win32') return false        // POSIX: NEVER shell — args pass through verbatim
  const normalized = cmd.trim().toLowerCase()
  return normalized.endsWith('.cmd') || normalized.endsWith('.bat')
}
// process.ts spawn:
const cmd = getPiCommand(params.piCommand)   // user override wins over platform default
spawn(cmd, args, { ..., shell: shouldUseShellForPiCommand(cmd) })
```

**Flow:** the override (`params.piCommand`, e.g. an absolute path from settings/tests) replaces only the EXECUTABLE name; the shell decision is then derived from the FINAL command string. On Windows, npm installs `pi` as `pi.cmd`; spawning a `.cmd`/`.bat` with `shell:false` fails (Node will not execute batch shims directly), so those get `shell:true`. Any other override on Windows (a real `.exe`) stays shell-less.

**Invariant:** shell is decided by SUFFIX on the resolved command, not by platform alone — forcing `shell:true` everywhere would expose args to cmd-style re-quoting/corruption and break argv passing; forcing it nowhere breaks Windows entirely. Case-insensitive suffix match because Windows paths arrive in any case.

**Probe:** `test/unit/new-session-pi-not-found.test.ts` + `test/unit/pi-command.test.ts` pin the command-resolution plumbing around spawn failure; the win32 branch itself is platform-gated (not executable on POSIX CI) — source-read verified; keep that caveat when porting.
**Coverage:** check_index_coverage `no_recorded_issue` + `metadata_match`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "defaultPiCommand shouldUseShellForPiCommand spawn shell", limit: 6, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt suffix-gated shell selection on the RESOLVED command with POSIX always shell-less. Adapt the binary name/override plumbing to your CLI. Omit nothing.
