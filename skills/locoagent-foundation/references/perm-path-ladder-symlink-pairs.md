<!-- capsule-v2 -->
# Path-permission ladder — symlink-pair checks, gitignore rule engine, internal carve-outs before safety

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** Given a Read/Edit request for a path that may be a symlink, contain `..`, use a Windows alias form, or live inside your own config directory — in what order do deny/ask rules, safety blocks, working-directory allows, and harness carve-outs evaluate so nothing can be bypassed?

## Path/Symbol
**Path/Symbol:** `src/utils/permissions/filesystem.ts` — `checkReadPermissionForTool` 8-step ladder (:1038-1202), `checkWritePermissionForTool` with steps 1.5/1.6/1.7 (:1213-1422), `matchingRuleForInput` ignore-library matching with `/**` restoration (:963-1033), `pathInWorkingPath` macOS /private normalization + case folding (:717-752), `getPathsForPermissionCheck` threading + memoized `getResolvedWorkingDirPaths` (:689-706), `checkEditableInternalPath` (:1489-1615), `checkReadableInternalPath` (:1621-1787), `getClaudeSkillScope` traversal/glob-metachar rejection (:101-162), `generateSuggestions` upgrade-only acceptEdits (:1424-1483).
**Signature:** `checkWritePermissionForTool(tool, input, context, precomputedPathsToCheck?) → PermissionDecision`.
**Data Shape:** Every check iterates `pathsToCheck` = ORIGINAL path ∪ realpath-resolved path (memoized for session-stable dirs); Read rules apply to any reading tool, Edit rules to any editing tool via tool-name indirection; patterns resolve per SOURCE root (`//`→filesystem root, `~/`→homedir, `/`→settings root, else CWD-relative, `./` stripped).

### Decisive source
```ts
// 3. Check for READ-SPECIFIC deny rules first - check both the original path and resolved symlink path
// SECURITY: This must come before any allow checks (including "edit access implies read access")
// to prevent bypassing explicit read deny rules
```

**Flow:** READ ladder: UNC early-block → suspicious-Windows-pattern block → read-deny (both paths) → read-ask → edit-implies-read ONLY after explicit read rules lose → working-dir allow → internal readable carve-outs (session memory, project dir, plan files, tool-results, scratchpad, project temp, agent/auto memory, tasks/, teams/, bundled-skills nonce root) → read allow rules → ask with dual-path suggestions. WRITE ladder: edit-deny → internal EDITABLE carve-outs BEFORE the dangerous-dir check (plan/scratchpad/job-dir/agent-memory/memdir/.claude/launch.json — several live under `.claude/` which is otherwise blocked) → session-scoped `.claude/**` or `/skills/**` allow bypasses safety (session-only sources searched deliberately so broader userSettings rules don't shadow it) → comprehensive safety check (`safetyCheck` decisionReason = bypass-immune upstream) → edit-ask → acceptEdits×working-dir allow → allow rules → ask.

**Invariant:** (1) Deny and ask rules are evaluated on BOTH original and resolved paths; an allow can never precede an explicit restriction. (2) Internal carve-outs MUST precede the safety check or the dangerous-`.claude/` classification eats them (step 1.5 comment says exactly this). (3) The `.claude/**` session bypass accepts narrowed skill patterns but rejects ANY `..` in content and requires the `/**` suffix. (4) Working-dir comparison resolves BOTH SIDES through the same symlink/case/macOS-/private normalization — asymmetric resolution produces false denials (documented at :700-706). (5) Skill-name extraction rejects `.`/`..`/glob metachars BEFORE interpolating into gitignore patterns (a dir named `*` would otherwise match ALL skills). (6) `setMode:acceptEdits` suggestions are suppressed outside default/plan modes because applying them from auto silently DOWNGRADES auto mode. (7) Precompute `pathsToCheck` ONCE per input and thread it — recomputation cost 30 syscalls/check; but only pass it for CANONICAL resolutions (stale values silently check the wrong path).

**Probe:** coverage caveat — no upstream unit tests reachable. Deterministic pins from repo root: `grep -nF 'including "edit access implies read access"' src/utils/permissions/filesystem.ts` → :1090; `grep -nF 'This MUST come before isDangerousFilePathToAutoEdit' src/utils/permissions/filesystem.ts` → :1250; `grep -nF 'silently' -e 'silent downgrade' src/utils/permissions/filesystem.ts | head -3` → :1453 & :1600; graph search `checkReadPermissionForTool` → filesystem.ts :1038-1202 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "matchingRuleForInput checkWritePermissionForTool pathInWorkingPath getPatternsByRoot", limit: 8 });
```

## Verdict
Adopt the dual-path (original+realpath) evaluation discipline, source-rooted pattern resolution over the ignore engine, carve-out-before-safety ordering, and symmetric working-dir resolution. Adapt the internal-path list to your harness's directories. Omit TEMPLATES job-dir hijack guards unless you have spawnable jobs, and desktop preview carve-outs.
