<!-- capsule-v2 -->
# Check-run upsert-by-name lifecycle — how do repeated (and batched) publications converge on ONE status report instead of many?

**Source:** qodana-action Apache-2.0 `main@e0675fbe…`; Codebase Memory `qodana-action`. **Question:** A CI job may publish results multiple times (annotation batches, retries). How does the GitHub Checks API get ONE authoritative check per run?

## listForRef → find(name) → update : create
**Path/Symbol:** `scan/src/utils.ts:publishGitHubCheck` (:682-708), `createCheck` (:718-734), `updateCheck` (:743-757); conclusion source `scan/src/annotations.ts:getGitHubCheckConclusion` (:206+, cited in sarif-output-projection); caller `scan/src/output.ts:publishOutput` slicing ≥50 annotations into MAX_ANNOTATIONS chunks.
**Signature:** `publishGitHubCheck(failedByThreshold: boolean, name: string, output: Output): Promise<void>`; internals take `(client, conclusion, …)`.
**Data Shape:** identity = check NAME on a head SHA (`pr.head.sha` when payload.pull_request exists, else `context.sha`); body always `{status:'completed', conclusion, output}`.

### Decisive source
```ts
const result = await client.rest.checks.listForRef({ ...github.context.repo, ref: sha })
const checkExists = result.data.check_runs.find(check => check.name === name)
if (checkExists) {
  await updateCheck(client, conclusion, checkExists.id, output)
} else {
  await createCheck(client, conclusion, sha, name, output)
}
// createCheck/updateCheck both send status:'completed' immediately — no in_progress phase
```

**Flow:** every publication resolves conclusion first (failure-if-threshold ELSE neutral-if-any-annotation ELSE success), then upserts by NAME against the PR head SHA. Because the 50-cap annotation batching in publishOutput re-enters this same function per slice, slices 2..n UPDATE the check created by slice 1 — batching stays idempotent precisely because identity is (name, sha), not content.
**Invariant:** Never create without listing first: Checks API allows multiple same-name runs on one ref, and blind creates would multiply checks per retry/batch. The head-SHA choice matters under pre-merged checkouts — pinning to `pr.head.sha` keeps the status on the contributed commit, not the merge ref (pairs with pr-base-resolution and merge-commit-pr-warning).
**Probe:** EXECUTED at pin: scan suite **11 passed** incl. the conclusion matrix; no upstream test drives publishGitHubCheck/createCheck/updateCheck themselves (Octokit network paths) — pinned by ranges + anchors above (coverage caveat). Deterministic anchor: `grep -n "listForRef" scan/src/utils.ts` → :698.
**Coverage caveat:** none — all cited paths no_recorded_issue, generation matches.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qodana-action", query: "publishGitHubCheck createCheck updateCheck checks listForRef", limit: 6 });
```
(exact 3-row result at execution time — rank order createCheck/updateCheck/publishGitHubCheck.)

## Verdict
Adopt name-keyed upsert-before-create for any idempotent CI status reporting (checks, deployments, external statuses); adapt identity fields to your API (name+ref here, external-id elsewhere); omit the immediate-completed posture only if you want progressive status, but then you own the timeout/failure transitions this design deliberately avoids.
