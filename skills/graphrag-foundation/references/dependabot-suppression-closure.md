<!-- capsule-v2 -->
# Dependabot suppression closure — how does graphrag close every open Dependabot PR without missing paginated results or partial failures?

**Source:** graphrag MIT `main@6dad6d2b059589624035714d8dcfde94ecc0a5fb`; Codebase Memory project `graphrag`. **Question:** How do you enumerate and close ALL open Dependabot PRs via the REST API such that pagination is exhausted before acting and a mid-loop failure cannot leave the run half-silent?

## Key facts
**Path/Symbol:** `scripts/close-dependabot-prs.ts` (`PullRequest` type :18-22; page loop :24-45; PATCH-close loop :47-70).
**Signature:** top-level module script — `const res = await fetch(...)` at module scope (Bun runs it directly: `bun run ./scripts/close-dependabot-prs.ts`); no exported function.
**Data Shape:** `PullRequest = { number: number; title: string; user: { login: string } | null }` — only three fields pulled from the list endpoint; author identity is read from `pr.user?.login` with optional-chaining because GitHub returns `"user": null` for deleted accounts.

### Decisive source
```ts
// scripts/close-dependabot-prs.ts :25-44 — collect-ALL-then-act, not act-per-page:
for (let page = 1; ; page++) {
  const pulls = (await res.json()) as PullRequest[];
  if (pulls.length === 0) {
    break;                                   // empty page = pagination exhausted
  }
  dependabotPrs.push(
    ...pulls.filter((pr) => pr.user?.login === DEPENDABOT_LOGIN),
  );
}
// :51-58 — per-PR close is a separate PATCH, and !res.ok THROWS mid-loop:
body: JSON.stringify({ state: "closed" }),
if (!res.ok) {
  throw new Error(`Failed to close PR #${pr.number}. ${res.status} - ${res.statusText}`);
}
```

**Flow:** throw-at-boot if `GH_APP_ACCESS_TOKEN` unset (:3-6) → paginate `/pulls?state=open&per_page=100&page=N`, filtering each page for `dependabot[bot]` authorship → break ONLY on an empty page → zero-match early exit prints "No open dependabot pull requests found." (:47-49) → else sequential PATCH `state:"closed"` per PR, logging each closure.
**Invariant:** enumeration completes BEFORE any mutation (the filter runs during collection, but closing starts only after the loop ends) — so re-running after a mid-loop crash closes the survivors, never skips unexamined pages. Auth failure and API failure are loud throws, never silent no-ops; the script is idempotent by construction (closing an already-closed PR is filtered out upstream because listing uses `state=open`).
**Probe:** `grep -c 'dependabot\[bot\]' scripts/close-dependabot-prs.ts` = 1 (the login constant :10); `grep -c 'state: "closed"' scripts/close-dependabot-prs.ts` = 1 (:56). No dedicated test suite exists for this script (coverage caveat: CI-workflow smoke only).

## Get live surrounding code
**Retrieve:** BM25 carries this TS file's tokens (unlike pure-doc nodes):
```ts
await mcp.codebase_memory.search_graph({ project: "graphrag", query: "dependabot pull request close state", limit: 10 });
```
rank#1 = `graphrag.scripts.close-dependabot-prs.PullRequest` line-exact.

## Verdict
Adopt collect-all-before-mutate + empty-page termination + loud per-item throws as the porting contract; adapt owner/repo constants and auth env-var name to host; omit the hardcoded `microsoft/graphrag` targeting (parameterize it). Coverage: `check_index_coverage` `no_recorded_issue`; no direct unit test pins this file.
