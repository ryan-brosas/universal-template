<!-- capsule-v2 -->
# AST permission ladder — bashToolHasPermission decision order

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** In what ORDER must deny rules, path constraints, subcommand checks, and asks be evaluated so no ordering re-arrangement creates a bypass?

## Path/Symbol
**Path/Symbol:** `src/tools/BashTool/bashPermissions.ts` — `bashToolHasPermission` (:1663-2557), `bashToolCheckPermission` per-subcommand (:1050-1180), `MAX_SUBCOMMANDS_FOR_SECURITY_CHECK = 50` (:103), `MAX_SUGGESTED_RULES_FOR_COMPOUND = 5` (:110), `filterCdCwdSubcommands` (:2153 region), shadow telemetry block (:1701-1739).
**Signature:** `bashToolHasPermission(input, context) → Promise<PermissionResult>`; behavior ∈ {allow, deny, ask, passthrough}.
**Data Shape:** `ParseForSecurityResult` → `astSubcommands: string[] | null`, `astRedirects`, `astCommands: SimpleCommand[]`; `astCommandsByIdx` maps filtered subcommand index → its SimpleCommand.

### Decisive source
```ts
// 2. Find all matching rules (prefix or exact)
// SECURITY FIX: Check Bash deny/ask rules BEFORE path constraints to prevent bypass
// via absolute paths outside the project directory (HackerOne report)
```

**Flow (the load-bearing ORDER):** ① parse once (`parseCommandRaw`) → `parseForSecurityFromAst`; too-complex ⇒ respect exact/prefix DENY first (`checkEarlyExitDeny`), then ask with the parser's reason — never downgrade a deny to ask. ② semantic fail ⇒ same deny-first shape (`checkSemanticsDeny`). ③ shadow feature mode records divergence telemetry then FORCES parse-unavailable (legacy stays authoritative, :1707-1739). ④ exact-match deny → prompt-rule deny/ask in parallel (deny precedence) → operator/pipe decomposition with post-allow re-validation of the ORIGINAL command (redirect targets stripped from segments would bypass: backtick-in-target + compoundCommandHasCd computed from FULL command not `false`, :1977-2046) → legacy misparse gate ONLY when AST absent → cd-cwd filtering + 50-subcommand cap (legacy path only; AST output is bounded by construction) → multiple-cd ask → **cd+git compound ask** (bare-repo core.fsmonitor escape; must run BEFORE per-subcommand readOnly re-derivation which sees compoundCommandHasCd=false, :2229-2250) → per-subcommand `bashToolCheckPermission` with AST argv → any-deny short-circuit → ORIGINAL-command redirect validation AFTER denies but BEFORE allow (:2288-2310) → GH#28784 rule: don't short-circuit on a path-constraint ask when a SUBCOMMAND independently asked (the Read-suggestion-only prompt silently approves python3) → single-non-allow short-circuit → merge flow collecting Bash rule suggestions capped at 5.

**Invariant:** (1) Deny rules are evaluated BEFORE every ask-producing check everywhere — an earlier ask would let out-of-project paths bypass explicit denies (H1 fix at :1072-1080). (2) Decomposition never skips whole-command validation: redirects/cd live on the ORIGINAL input and are checked after segment allows. (3) Compound-context flags (cd+git, compoundCommandHasCd) must derive from the full command, never from an individual segment. (4) When several asks exist, surface ALL their suggestions (merge flow) rather than the first ask's narrow Read rule. (5) Fanout caps apply ONLY to unbounded (legacy split) paths.

**Probe:** coverage caveat — no upstream unit tests. Pins: `grep -nF 'SECURITY FIX: Check Bash deny/ask rules BEFORE path constraints' src/tools/BashTool/bashPermissions.ts` → :1073; `grep -nF 'bare repository attacks' src/tools/BashTool/bashPermissions.ts` → :2217; `grep -nF 'silently approves' src/tools/BashTool/bashPermissions.ts` → :2300; graph `search_graph --project locoagent --query bashToolHasPermission` → :1663-2557 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "bashToolHasPermission bashToolCheckPermission checkPathConstraints checkEarlyExitDeny", limit: 5 });
```

## Verdict
Adopt the ordering skeleton wholesale for any tool-permission checker that combines static analysis, rule matching, and path constraints. The order IS the security property; the specific rules are policy.
