<!-- capsule-v2 -->
# Platform-adapter fan-out — how does one codebase keep three CI integrations in sync without an abstraction layer?

**Source:** qodana-action Apache-2.0 `main@829c6a56…`; Codebase Memory `qodana-action`. **Question:** What is genuinely shared vs deliberately duplicated across the GitHub/GitLab/Azure adapters, and what does each host uniquely own?

## Shared common/ core + three parallel utils.ts with identical function NAMES
**Path/Symbol:** shared `common/{qodana,output,utils}.ts` (~1.1k LOC); adapters `scan/src/utils.ts` (818L), `gitlab/src/utils.ts` (641L), `vsts/src/utils.ts` (622L); entry points `*/src/main.ts` (123/63/78L); API clients `gitlab/src/gitlabApiProvider.ts` + `vsts/src/gitApiProvider.ts` (module-memoized lazy singletons).
**Signature:** every adapter exports the same verb set: `getInputs, prepareAgent, qodana(qodanaScan), pushQuickFixes, postResultsToPRComments, findCommentByTag, uploadArtifacts, getWorkflowRunUrl`.
**Data Shape:** one `Inputs` interface (common/qodana.ts :266-286) with per-platform unused fields zeroed ('not used by the action' comments).

### Decisive source
```ts
// gitlab/src/gitlabApiProvider.ts — the whole file
let gitlabApi: InstanceType<typeof Gitlab> | null = null
function initApi(): InstanceType<typeof Gitlab> { ... gitlabApi = gitlab; return gitlab }
export function getGitlabApi(): InstanceType<typeof Gitlab> {
  const api = gitlabApi
  if (!api) return initApi()
  return api
}
```
Graph evidence of the twin structure — search_graph "merge-base pull request sha" returns FOUR getPrSha implementations at consistent ranks:
```
qodana-action.gitlab.src.utils.getPrSha  gitlab/src/utils.ts 338-367
qodana-action.scan.src.utils.getPrSha    scan/src/utils.ts   132-182
qodana-action.vsts.src.utils.getPrSha    vsts/src/utils.ts   275-308
(+ compiled bundle twin vsts/QodanaScan/index.js)
```

**Flow:** pure logic (arg parsing, exit-code semantics, checksum/URL builders, SARIF parsing, summary markdown, comment tags) lives in `common/` and is imported unchanged by all three. Host-specific mechanics are DUPLICATED under identical names so a reader diffs `scan/src/utils.ts` against `gitlab/src/utils.ts` line-for-line: input reading (@actions/core vs env vars vs task-lib), CLI install (tool-cache vs axios+AdmZip vs tool-lib), exec (getExecOutput vs spawn vs tl.execAsync), comments (issues API vs discussions+resolve vs threads+status). Each adapter registers its deprecation-warning emitter and memoizes inputs at module scope.
**Invariant:** Duplication is a FEATURE here: no leaky abstraction over three SDKs whose verbs differ subtly (GitHub update-vs-create check runs; GitLab discussion RESOLVE state; Azure thread STATUS enum). The sync burden is managed by keeping function names/signatures identical — porters adding a fourth platform should copy the closest adapter whole, then swap mechanics, NOT extract an interface first.
**Probe:** graph probe above (4-twin resolution); parity by name: grep each adapter for `export async function` yields matching verb sets (deterministic check executed this pass); behavior differences pinned inside their respective capsules.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qodana-action", query: "prepareAgent pushQuickFixes postResultsToPRComments", limit: 12 });
```

## Verdict
Adopt "shared-pure-core + named-identical duplicated adapters" when targeting ≥3 hosts with divergent SDKs; adapt which verbs move into common as your hosts converge; omit premature abstraction — the repo's own evolution (bundle checked into vsts/) shows the maintenance cost lives in mechanics, not contracts.
