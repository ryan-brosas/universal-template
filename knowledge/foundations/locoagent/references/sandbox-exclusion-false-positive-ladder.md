<!-- capsule-v2 -->
# Sandbox exclusion exemption ladder — when is a Bash command exempt from sandboxing, and why is that exemption NOT a security boundary?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** When must a Bash command be exempted from sandboxing (excludedCommands / dangerouslyDisableSandbox), and what makes the exemption safe to bypass?

## Exemption decision ladder
**Path/Symbol:** `src/tools/BashTool/shouldUseSandbox.ts` : `shouldUseSandbox` (:130-153) + `containsExcludedCommand` (:21-128).
**Signature:** `function shouldUseSandbox(input: Partial<SandboxInput>): boolean` over `SandboxInput { command?: string; dangerouslyDisableSandbox?: boolean }`.
**Data Shape:** `settings.sandbox.excludedCommands: string[]` holding Bash-permission-rule patterns parsed via `bashPermissionRule` (prefix `cmd:*` / exact / wildcard); ant-only dynamic feature flag `{ commands: string[], substrings: string[] }`.

### Decisive source
```ts
// NOTE: excludedCommands is a user-facing convenience feature, not a security boundary.
// It is not a security bug to be able to bypass excludedCommands — the sandbox permission
// system (which prompts users) is the actual security control.
```

**Flow:** Gate order in `shouldUseSandbox`: (1) global off-switch — `SandboxManager.isSandboxingEnabled()` false ⇒ false; (2) `dangerouslyDisableSandbox` honored ONLY when policy `areUnsandboxedCommandsAllowed()` also allows it (both must agree); (3) empty command ⇒ false; (4) `containsExcludedCommand` ⇒ false; else true. Inside the exclusion check: ant-only dynamic disabled substrings (`command.includes`) then per-subcommand base-name matches run FIRST; user `excludedCommands` are matched per SUBCOMMAND (`splitCommand_DEPRECATED` splits compound commands so `docker ps && curl evil.com` cannot ride a matching first segment), and each subcommand is expanded into a candidate SET iterated to fixed point — `stripAllLeadingEnvVars(cmd, BINARY_HIJACK_VARS)` and `stripSafeWrappers(cmd)` applied repeatedly until no new candidates — so interleaved forms like `timeout 300 FOO=bar bazel run` still match `bazel:*`.

**Invariant:** (1) The exemption is deliberate convenience surface: bypassing it is not a vuln because the permission-prompt system remains the real control — a porter who hardens this check breaks UX, one who trusts it for security creates a hole. (2) Parse failure falls OPEN here (malformed bash syntax ⇒ treat as not excluded) so rendering never crashes; other validation layers handle the command. (3) Hijack-class env vars (`LD_*`, `DYLD_*`, `PATH`) are never stripped (blocklist regex), and wrapper/env stripping uses horizontal-whitespace-only `[ \t]` anchors so newline-separated second commands cannot be swallowed into a candidate.

**Probe:** anchored at the locoagent repo root — `grep -n 'not a security boundary' src/tools/BashTool/shouldUseSandbox.ts` → :18; `grep -n 'const candidates' src/tools/BashTool/shouldUseSandbox.ts` → :82; `grep -n 'while (startIdx < candidates.length)' src/tools/BashTool/shouldUseSandbox.ts` → :85; `grep -c BINARY_HIJACK_VARS src/tools/BashTool/shouldUseSandbox.ts` → 3; `grep -n 'USER_TYPE' src/tools/BashTool/shouldUseSandbox.ts | head -1` → :23; `grep -n 'dangerouslyDisableSandbox &&' src/tools/BashTool/shouldUseSandbox.ts` → :137; `grep -n 'isSandboxingEnabled()' src/tools/BashTool/shouldUseSandbox.ts` → :131.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "shouldUseSandbox excludedCommands containsExcludedCommand", limit: 5 });
```

## Verdict
Adopt the gate ORDER (enable-check → policy-gated override → exclusion ladder) and the fixed-point candidate expansion for wrapper/env interleaving; adapt the ant-only dynamic flag channel to your own feature-flag service; omit the deprecated `splitCommand_DEPRECATED` dependency (port against your parser). Direct-test caveat: no upstream unit tests for this file; probes pin line-exact source anchors instead.
