<!-- capsule-v2 -->
# PS git external-command safety — how does a PowerShell allowlist validate git/gh/docker flags without re-implementing each binary's parser?

**Source:** LocoAgent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** How do shared read-only command tables serve a second shell, and which PowerShell-side differentials (global-flag skipping, `$` expansion, PATHEXT twins) must the adapter close?

## Shared tables + PS-side global-flag cursor with attached-short-flag rejection
**Path/Symbol:** `src/tools/PowerShellTool/readOnlyValidation.ts`: `CMDLET_ALLOWLIST['git'|'gh'|'docker'|'dotnet']: {}` (:683-875) → `isExternalCommandSafe` dispatch (:1522-1535) → `isGitSafe` (:1584-1701: DANGEROUS_GIT_GLOBAL_FLAGS :1537-1553, GIT_GLOBAL_FLAGS_WITH_VALUES :1566-1576, DANGEROUS_GIT_SHORT_FLAGS_ATTACHED :1582, ls-remote URL guard :1679-1692), `isGhSafe` (:1703-1757), `isDockerSafe` (:1759-1807), `isDotnetSafe` (:1809-1823).
**Signature:** `function isGitSafe(args: string[]): boolean` etc.; flag validation delegated to the SHARED `validateFlags` walker (`ro-flagmap-validateflags.md`) over `GIT_READ_ONLY_COMMANDS`/`GH_READ_ONLY_COMMANDS`/`DOCKER_READ_ONLY_COMMANDS`.
**Data Shape:** Args are post-stringify tokens; bare Variable positionals arrive as literal text (`$env:SECRET`) because deriveSecurityFlags never gated them.

### Decisive source
```ts
// SECURITY: Attached-form short flags. `-ccore.pager=sh` splits on `=` to
// `-ccore.pager`, which isn't in DANGEROUS_GIT_GLOBAL_FLAGS. Git accepts
// `-c<name>=<value>` and `-C<path>` with no space. We must prefix-match.
// ... It does NOT apply to `-C` — directory paths CAN start with `-`, so
// `git -C-trap status` must reject.
for (const shortFlag of DANGEROUS_GIT_SHORT_FLAGS_ATTACHED) {
  if (
    arg.length > shortFlag.length &&
    arg.startsWith(shortFlag) &&
    (shortFlag === '-C' || arg[shortFlag.length] !== '-')
  ) { return false }
}
```

**Flow:** blanket `$` rejection across ALL args first (parser differential: validator sees literal `$VAR`, PowerShell expands at runtime — `docker ps --format $env:AWS_SECRET_ACCESS_KEY` printed secrets through error output before this moved BEFORE docker's fast-path) → skip global flags pre-subcommand, consuming space-separated values so they aren't mistaken for subcommands, rejecting dangerous ones outright incl. the `--attr-source` parser differential (git treats the next token as pathspec; validator would see `log` as subcommand while git runs `status`) → two-word-then-one-word subcommand lookup in shared tables → shell-specific guards (ls-remote URL/`@`/`:`/`$` exfil rejection) → shared `validateFlags`. Canonicalization feeds it via `resolveToCanonical`, whose PATH-FREE-only PATHEXT strip makes `git.exe` trigger git safety while `scripts\git.exe` does not.
**Invariant:** The value-consuming-global-flags set MUST be complete — any missing member creates a validator-vs-binary subcommand differential. `USER_TYPE !== 'ant'` gates gh entirely. dotnet allows only its four top-level introspection flags.
**Probe:** `grep -nF "'--attr-source'," src/tools/PowerShellTool/readOnlyValidation.ts` → :1552 and `grep -cF 'if (arg.includes('"'"'$'"'"'))' src/tools/PowerShellTool/readOnlyValidation.ts` → `3` (git/gh/docker; dotnet uses a set-membership form instead) and `grep -nF "const WINDOWS_PATHEXT = " src/tools/PowerShellTool/readOnlyValidation.ts` → :973 (anchored at the locoagent repo root).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "isGitSafe DANGEROUS_GIT_GLOBAL_FLAGS attr-source", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt shared-table reuse plus the shell-specific differentials ($ rejection placement, global-flag cursor completeness, attached short-flag prefix matching). Adapt table keys per your registry. Omit man-page audit notes beyond the completeness invariant. Coverage caveat: probes deterministic; graph confirms `isGitSafe` :1584-1701 rank#1 line-exact.
