<!-- capsule-v2 -->
# Hook execution core — how are user shell hooks run, parsed, deduped, and made safe?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How does the hook engine execute five hook types (command/prompt/agent/http/callback) with one output contract, and which guards prevent untrusted or duplicate hooks from executing?

## executeHooks + getMatchingHooks + execCommandHook
**Path/Symbol:** `src/utils/hooks.ts` — `executeHooks` (:1952-2972, in-REPL generator), `executeHooksOutsideREPL` (:3003-3381), `getMatchingHooks` (:1603-1874), `execCommandHook` (:747-1335), `processHookJSONOutput` (:489-737), `parseHookOutput` (:399-451), `matchesPattern` (:1346-1381), `hookDedupKey` (:1453-1455), `shouldSkipHookDueToTrust` (:286-296), `hasHookForEvent` (:1582-1593).
**Signature:** `executeHooks({hookInput, toolUseID, matchQuery, signal?, timeoutMs?, toolUseContext?, messages?, forceSyncExecution?, requestPrompt?}): AsyncGenerator<AggregatedHookResult>` — yields progress per matched hook FIRST, then one aggregate per completed hook.
**Data Shape:** `AggregatedHookResult` = {message?, systemMessage?, blockingError?, outcome: 'success'|'blocking'|'non_blocking_error'|'cancelled', preventContinuation?, stopReason?, permissionBehavior?: allow/deny/allow/passthrough, additionalContexts?, initialUserMessage?, updatedInput?, updatedMCPToolOutput?, watchPaths?, retry?, elicitationResponse?...}.

### Decisive source
```ts
// :166 + :175 session-end budget
const TOOL_HOOK_EXECUTION_TIMEOUT_MS = 10 * 60 * 1000
const SESSION_END_HOOK_TIMEOUT_MS_DEFAULT = 1500   // shutdown cannot wait 10min; env-overridable

// :1453-1455 dedup key namespacing (gh-29724)
// Settings-file hooks share the '' prefix so the same command defined in
// user/project/local still collapses to one ... Plugin/skill hooks get their
// root as the prefix, so two plugins sharing an unexpanded template don't collapse.
return `${m.pluginRoot ?? m.skillRoot ?? ''}\0${payload}`

// :1748-1752 shell is part of command-hook identity
// {command:'echo x', shell:'bash'} and {command:'echo x', shell:'powershell'}
// are distinct hooks. Default to 'bash' so legacy configs still dedup.
`${m.hook.shell ?? DEFAULT_HOOK_SHELL}\0${m.hook.command}\0${getIfCondition(m.hook)}`
```

**Flow:** global kill-switches (disableAllHooks managed setting → CLAUDE_CODE_SIMPLE → workspace trust gate for ALL interactive hooks — RCE defense citing SessionEnd/SubagentStop pre-trust vulns) → hasHookForEvent over-approximate existence check skips transcript-path joins on hot paths → getMatchingHooks assembles snapshot+registered+session hooks (managed-only filters pluginRoot matchers; session function hooks skipped entirely under managedOnly) → matchQuery derived per event (tool_name / source / trigger / notification_type / reason / error / agent_type / basename(file_path)) filtered by matchesPattern (pipe-list exact w/ legacy-name normalize, else regex incl. legacy-name alternates; invalid regex ⇒ no-match not crash) → dedup via 4 Map passes keyed on source\0(shell\0command|prompt|url)\0if-condition — callback/function hooks skip dedup entirely (fast path measured 6µs→1.8µs) → `if:` conditions evaluated through prepareIfConditionMatcher's ONCE-per-event expensive prep (tool lookup + zod parse + tree-sitter bash matcher closure); non-tool events with if-conditions are DROPPED loud → HTTP hooks banned on SessionStart/Setup (sandbox ask-callback deadlock) → parallel execution: command (execCommandHook spawn w/ GitBash-on-Windows POSIX path conversion, .sh auto-prepend, ${CLAUDE_PLUGIN_ROOT}/${user_config.X} substitution ordered plugin-first, CLAUDE_ENV_FILE for env-mutating events only, deleted-cwd fallback to original cwd, async-protocol detection parses ONLY the first line containing '}' else fast hooks block full-duration, asyncRewake bypasses registry and re-enters queue as task-notification on exit-code-2, prompt-request lines intercepted from stdout then stripped by CONTENT-match fail-closed set), prompt/agent (LLM-backed via toolUseContext+messages), http (JSON-only body validated through same schema; own timeout — parent signal passed raw to avoid double-stacking), callback/function (in-process; function hooks boolean-pass/fail→blockingError) → processHookJSONOutput maps JSON to effects: continue:false⇒preventContinuation; decision approve/block + hookSpecificOutput.permissionDecision ladder (deny sets blockingError; unknown values THROW) ; expectedHookEvent mismatch throws; exit code 2 = blocking stderr feedback; other non-zero = non_blocking_error attachment.

**Invariant:** (1) Trust-gate is centralized BEFORE matching — captured-snapshot hooks can't leak past a declined trust dialog. (2) Dedup identity = source-context + shell + payload + if-condition; last-writer-wins via Map semantics (settings scope merge order decides). (3) Async protocol is first-line-only by construction (comment documents the full-buffer bug). (4) Missing plugin root throws PRE-spawn because python3-missing-script exits 2 = indistinguishable-from-intentional-block after spawn (would brick Stop/UserPromptSubmit until restart). (5) Outside-REPL twin returns plain results (no model-visible attachments): blocked = exit2 OR JSON decision:block; WorktreeCreate consumers read stdout as a bare path (HTTP variant reads hookSpecificOutput.worktreePath; empty string beats raw '{}' body). (6) executeStopHooks threads stop_hook_active to prevent recursion; SubagentStop keys agent_id+transcript+type; PreCompact hooks may REWRITE custom instructions (successful outputs joined '\n\n'); ConfigChange hooks fire for audit but policy-source blocking results are ignored (policy settings never blockable).

**Probe:** coverage caveat — no upstream tests for this file. Deterministic pins: `grep -n "gh-29724" src/utils/hooks.ts` (:1714); `grep -n "SESSION_END_HOOK_TIMEOUT_MS_DEFAULT = 1500" src/utils/hooks.ts` (:175); `grep -n "indistinguishable from an" src/utils/hooks.ts` (:829); `grep -n "Check for async response on first line" src/utils/hooks.ts` (:1112); graph resolves executeHooks/getMatchingHooks/execCommandHook/processHookJSONOutput line-exact under `src.utils.hooks`.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "executeHooks execCommandHook hookDedupKey matchesPattern", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt trust-before-execute, namespaced dedup keys, exit-2-as-block with non-zero-as-non-blocking, first-line async detection, and pre-spawn existence checks for templated roots; adapt shell/platform plumbing and event vocabulary; omit StatusLine/FileSuggestion command surfaces unless porting the UI too. Porting trap: deduping across plugin boundaries by command text alone drops distinct plugins sharing a template; treating any non-zero exit as blocking silences entire workflows on cosmetic failures.
