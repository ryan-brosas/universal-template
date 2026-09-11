<!-- capsule-v2 -->
# $-token rejection & xargs target contract — why every `$` in a token voids the whole validation, and how xargs pipelines stay provable

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** The tokenizer preserves `$VAR` as literal text while bash expands it at runtime — which tokens can you actually vouch for, and what makes an `xargs` tail safe?

## Path/Symbol
**Path/Symbol:** `src/tools/BashTool/readOnlyValidation.ts` inside `isCommandSafeViaFlagParsing` (:1246-1408) — glob-token normalization (:1253-1261), operator rejection (:1266-1269), longest-prefix command match (:1282-1300), the ALL-tokens `$` + brace-expansion sweep (:1328-1369), xargs wiring (:1372-1381); `SAFE_TARGET_COMMANDS_FOR_XARGS` const (:1232-1239); `getCommandAllowlist` Windows-xargs removal + ant-only merge (:1201-1215); shared walker's xargs branch (`src/utils/shell/readOnlyCommandValidation.ts` :1703-1717); backtick/newline guards (:1383-1396).
**Signature:** `isCommandSafeViaFlagParsing(command: string): boolean` (internal); `xargsTargetCommands?: string[]` option.
**Data Shape:** tokens from `tryParseShellCommand(command, env => \`$${env}\`)` with `{op:'glob'}` objects flattened to their pattern strings; ANY remaining non-string token (operator) ⇒ reject.

### Decisive source
```ts
// SECURITY: Reject ANY token containing `$` (variable expansion). The
// `env => `$${env}`` callback at line 825 preserves `$VAR` as LITERAL TEXT
// in tokens, but bash expands it at runtime (unset vars → empty string).
// This parser differential defeats BOTH validateFlags and callbacks:
//
//   (1) `$VAR`-prefix defeats validateFlags `startsWith('-')` check:
//       `git diff "$Z--output=/tmp/pwned"` → ... ARBITRARY FILE WRITE.
//   (2) `$VAR`-prefix → RCE via `rg --pre`:
//       `rg . "$Z--pre=bash" FILE` → executes `bash FILE`. ...
//   (3) `$VAR`-infix defeats additionalCommandIsDangerousCallback regex:
//       `ps ax"$Z"e` → token `ax$Ze`. ... A fix limited to `$`-PREFIXED
//       tokens would NOT close this.
```
```ts
const SAFE_TARGET_COMMANDS_FOR_XARGS = [
  'echo',    // Output only, no dangerous flags
  'printf',  // xargs runs /usr/bin/printf (binary), not bash builtin — no -v support
  'wc', 'grep', 'head',
  'tail',    // Read-only (including -f follow), no dangerous flags
]
```

**Flow:** parse → reject operators → match command config by LONGEST multi-word prefix → ls-remote URL/SSH/`$` positional guard (git-specific) → sweep EVERY post-command token: contains `$` ⇒ reject; contains `{` AND (`,` or `..`) ⇒ brace-expansion reject → validateFlags with `commandName` and (for xargs only) SAFE_TARGET_COMMANDS_FOR_XARGS: once the walker hits a non-flag (or `--` then next), that token must be one of the six targets or the command fails; on match, validation STOPS — hence the list requires commands with NO dangerous flags at all, not just a safe subset.

**Invariant:** (1) You cannot approve a token whose runtime value you cannot compute — `$` ANYWHERE in a token (prefix, infix, suffix) invalidates the whole command. (2) Stopping flag-validation at the xargs target transfers FULL responsibility to the target list: membership demands zero dangerous flags across the binary's entire surface ("verified by checking its man page"). (3) Platform asymmetry is deliberate: Windows drops xargs entirely because UNC paths hide INSIDE FILE CONTENTS piped through xargs (`cat file | xargs cat` → SMB credential leak) where no string regex can see them. (4) Backtick rejection applies whenever the entry has no custom regex; grep/rg additionally reject `\n`/`\r` (pattern injection).

**Probe:** no upstream tests reachable — coverage caveat. Pins from repo root: `grep -nF "check must run BEFORE validateFlags and BEFORE callbacks" src/tools/BashTool/readOnlyValidation.ts` → :1350; `grep -nF "brace expansion obfuscation" src/tools/BashTool/readOnlyValidation.ts` → :1358; `grep -nF "On Windows, xargs can be used as a data-to-code bridge" src/tools/BashTool/readOnlyValidation.ts` → :1203.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "isCommandSafeViaFlagParsing", limit: 4 });
// → :1246-1408 sole hit line-exact
```
Note: `SAFE_TARGET_COMMANDS_FOR_XARGS` is a module const — BM25-invisible like pass 17's `getCommandSpec`; cite :1232-1239 directly.

## Verdict
Adopt the reject-all-$-tokens rule, brace-expansion pair check, and the man-page-verified xargs target contract. Adapt the target list to your host's binaries (re-verify each). Omit the Windows carve-out only on non-Windows hosts — but keep the comment so a future port doesn't re-enable it there.
