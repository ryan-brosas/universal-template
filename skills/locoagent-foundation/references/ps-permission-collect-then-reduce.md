<!-- capsule-v2 -->
# PS permission collect-then-reduce — how do you order deny/ask/allow decisions so an early ask can never mask a later deny?

**Source:** LocoAgent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** How do you structure a shell-tool permission function so every check runs, precedence is structural, and no early return can bury a stronger decision behind a weaker one?

## Push ALL post-parse decisions into one array; reduce enforces deny > ask > allow
**Path/Symbol:** `src/tools/PowerShellTool/powershellPermissions.ts`:`powershellToolHasPermission` (:639-1648), decisions array + reduce (:876-1368); pre-parse gates (:659-757); step-5 per-sub-command loop (:1370-1626).
**Signature:** `async function powershellToolHasPermission(input: { command: string; timeout?: number }, context: ToolUseContext): Promise<PermissionResult>`.
**Data Shape:** `decisions: PermissionResult[]` — every post-parse check pushes at most one decision (deferred pre-parse ask, security battery, using/#Requires asks, provider/UNC scan, per-sub-command rules, cd+git / bare-repo / git-internal-write / archive-extractor guards, path constraints, exact-allow, read-only allow, redirections ask, acceptEdits allow). Reduce: first `deny`, else first `ask`, else first `allow`, else fall through to step 5.

### Decisive source
```ts
// COLLECT-THEN-REDUCE: ... This structurally closes the ask-before-deny bug
// class: an 'ask' from an earlier check (security flags, provider paths, cd+git)
// can no longer mask a 'deny' from a later check (sub-command deny,
// checkPathConstraints). Supersedes the firstSubCommandAskRule stash from commit
// 8f5ae6c56b — that fix only patched step 4; steps 3, 3.5, 4.42 had the same flaw.
// The stash pattern is also fragile: the next author who writes `return ask` is
// back where we started. Collect-then-reduce makes the bypass impossible to write.
const deniedDecision = decisions.find(d => d.behavior === 'deny')
if (deniedDecision !== undefined) {
  return deniedDecision
}
```

**Flow:** empty⇒allow → parse once → EXACT/prefix DENY rules fire pre-parse (raw string; works even when pwsh is unavailable) → prefix-ask and raw UNC ask DEFERRED into the array (previously early returns let them mask sub-command denies) → if parse failed: fallback fragment scan (backtick-aware collapse of line continuations then split on `[;|\n\r{}()&]+`, assignment/dot-source/call-operator normalization per fragment, parse-independent dangerous-removal hard-deny on raw positional args) before returning the generic parse-error ask → post-parse: push everything, reduce → step 5 checks each remaining sub-command independently with its own fail-closed statement gate.
**Invariant:** Deny rules operate on raw text BEFORE validity so explicit denies survive parser loss; asks defer but allows NEVER skip ahead of sub-command deny checks (the parse-failed exact-allow short-circuit additionally requires `!parsed.valid && preParseAskDecision === null && classifyCommandName(first token) !== 'application'`). First-of-behavior-wins preserves single-check messaging while the reduce makes masking unwritable.
**Probe:** `grep -nF "COLLECT-THEN-REDUCE" src/tools/PowerShellTool/powershellPermissions.ts` → :877 and `grep -nF "PS_ASSIGN_PREFIX_RE = " src/tools/PowerShellTool/powershellPermissions.ts` → :62 and `grep -cF "statementsSeenInLoop.add" src/tools/PowerShellTool/powershellPermissions.ts` → `4` (anchored at the locoagent repo root).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "powershellToolHasPermission decisions reduce deny ask", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt collect-then-reduce as THE shape for any multi-gate permission funnel (it is portable far beyond PowerShell), plus the pre-parse-deny/post-parse-collect split. Adapt rule-matching internals to your rule grammar. Omit BashTool-parity cross references. Coverage caveat: no unit tests in-repo; graph confirms `powershellToolHasPermission` :639-1648 rank#1.
