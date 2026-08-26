<!-- capsule-v2 -->
# Rule suggestion shaping — stable prefixes for heredoc/multiline commands

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do you turn a one-off command approval into a REUSABLE rule suggestion that will actually match future invocations without corrupting settings?

## Path/Symbol
**Path/Symbol:** `src/tools/BashTool/bashPermissions.ts` — `suggestionForExactCommand` (:271-299), `extractPrefixBeforeHeredoc` (:305-340), `getSimpleCommandPrefix` (:161-190, subcommand shape `/^[a-z][a-z0-9]*(-[a-z0-9]+)*$/`), compound merge cap (:2480-2520 region).
**Signature:** `suggestionForExactCommand(command) → PermissionUpdate[]` (prefix rule preferred; exact rule last resort).
**Data Shape:** `PermissionUpdate { type: 'addRules', rules, behavior: 'allow', destination: 'localSettings' }`.

### Decisive source
```ts
// Heredoc commands contain multi-line content that changes each invocation,
// making exact-match rules useless (they'll never match again). Extract a
// stable prefix before the heredoc operator and suggest a prefix rule instead.
//
// Multiline commands without heredoc also make poor exact-match rules.
// Saving the full multiline text can produce patterns containing `:*` in
// the middle, which fails permission validation and corrupts the settings
// file. Use the first line as a prefix rule instead.
```

**Flow:** ladder: heredoc present ⇒ prefix = tokens BEFORE `<<` (safe-env-var-skipping 2-token fallback preserving flags like `python3 -c`) → newline present ⇒ FIRST LINE as prefix → single line ⇒ 2-word `cmd subcmd` prefix when the second token is a subcommand-shaped word (not flag/path/number/URL) ⇒ else exact rule. In the compound-ask merge flow, security asks with NO suggestions synthesize a Bash(exact) rule so the prompt names the chained command instead of only the cd target's Read rule (GH#28784 follow-up); explicit ask rules are skipped (user wants per-time review). Collected rules dedupe by string key, preserve insertion order, cap at MAX_SUGGESTED_RULES_FOR_COMPOUND=5 keeping leftmost.

**Invariant:** (1) A saved rule must be STABLE across invocations — exact-matching volatile content mints dead rules. (2) Never embed `:*` mid-pattern (multiline text does) — it fails validation and corrupts settings files. (3) Suggestion breadth is asymmetric: too-narrow annoys, too-broad grants — prefer the narrowest STABLE prefix (`git commit`, not `git`). (4) Security-sourced asks need a synthesized visible rule or users approve blind via an unrelated Read option. (5) Prefix extraction must skip env vars with the SAME allowlist as matching (dead-rule prevention).

**Probe:** coverage caveat — no upstream unit tests. Pins: `grep -nF 'corrupts the settings' src/tools/BashTool/bashPermissions.ts` → :277; `grep -nF 'never match again' src/tools/BashTool/bashPermissions.ts` → :268; `grep -c 'MAX_SUGGESTED_RULES_FOR_COMPOUND' src/tools/BashTool/bashPermissions.ts` ≥ 3; graph `search_graph --project locoagent --query extractPrefixBeforeHeredoc getSimpleCommandPrefix` line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "extractPrefixBeforeHeredoc suggestionForExactCommand getSimpleCommandPrefix", limit: 5 });
```

## Verdict
Adopt the stability ladder (heredoc-prefix → first-line → two-word subcommand → exact) plus the security-ask synthesis rule for any permission UX that saves rules from prompts.
