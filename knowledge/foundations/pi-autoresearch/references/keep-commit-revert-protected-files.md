<!-- capsule-v2 -->
# Keep-commits / everything-else-reverts — how does git make the agent's keep/discard decision physical?

**Source:** pi-autoresearch-harness MIT `main@511760df8905c7b6e6bbd3a028de734becff69e6`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness`. **Question:** What exactly happens to the working tree on `keep` vs any non-keep status, and which files must survive a revert?

## dispatchAction log tail — add -A/commit on keep; stage-guard + checkout/clean otherwise
**Path/Symbol:** `harness/server.ts:dispatchAction('log')` — commit branch :1374–1412, revert branch :1414–1429, `getProtectedFiles` :590–598.
**Signature:** `gitExec(['add','-A'])` → `gitExec(['diff','--cached','--quiet'])` → `commit -m "<description>\n\nResult: <json>"`; else `add -- <protected…>` → `checkout -- .` → `clean -fd`.
**Data Shape:** commit message embeds machine-readable results: `{status, [metricName]: metric, ...secondaryMetrics}`; protected set = `autoresearch.jsonl, autoresearch.md, autoresearch.ideas.md, autoresearch.sh, autoresearch.checks.sh`.

### Decisive source
```ts
if (status !== 'keep') {
  // re-stage session files so checkout--. cannot roll them back
  for (const file of getProtectedFiles()) {
    if (fs.existsSync(join(workDir, file))) gitExec(['add', '--', file], workDir);
  }
  const checkoutResult = gitExec(['checkout', '--', '.'], workDir);
  const cleanResult = gitExec(['clean', '-fd'], workDir);
```
(verbatim at :1420–1421 — note the deliberate order: protected files staged BEFORE `checkout -- .`, then `-fd` sweeps untracked debris.)

**Flow:** keep → `git add -A`; clean tree reports "nothing to commit" (:1390–1392) instead of failing; commit succeeds → experiment.commit RE-STAMPED from new HEAD short sha (:1398–1403) so the row points at the code that produced the metric; commit failure degrades to a warning line, the log itself still stands. Non-keep (discard/crash/checks_failed) → protected five staged first → `checkout -- .` discards tracked modifications → `clean -fd` removes untracked files → message "reverted changes (<status>)".
**Invariant:** the five session files are the loop's memory and MUST survive an arbitrary discard — staging them before checkout is what makes `checkout -- .` safe; a porter who reverts without the pre-stage wipes the experiment ledger mid-loop. Commit re-stamp after commit means `experiment.commit` can differ from `session.startingCommit` (captured pre-run :938–946) — the starting value is only a fallback for 'unknown'. Clean-tree keep is legal and produces NO commit (idempotent re-log protection).
**Probe:** anchors: `grep -n startingCommit harness/server.ts | cut -d: -f1` → :70 (SessionState field), :354 (createSessionState), :938 + :944 (run capture), :1276 (log fallback read), :1450 (post-log clear) — six lines; `grep -n "getProtectedFiles" harness/server.ts` → :590 + :1417; `grep -n "'checkout', '--', '.'" harness/server.ts` → :1420; `grep -n "'clean', '-fd'" harness/server.ts` → :1421; `grep -n 'Result: ' harness/server.ts` → :1382 (single site).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness", query: "getProtectedFiles checkout clean reverted changes", limit: 10 });
```

## Verdict
Adopt the protected-set-before-revert ordering and the Result:-JSON commit message verbatim (the message doubles as the machine log — later tooling greps it); adapt the protected filename list to your own session-file names; omit Windows path normalization only if unported. No direct test drives the git plane (`__tests__/integration/worktree.test.ts` covers creation/detection, not commit/revert) — treat the ordering as source-pinned.
