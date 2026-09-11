<!-- capsule-v2 -->
# Version-consistency doc tests — how do README/orb version mentions stay in lockstep with releases?

**Source:** qodana-action Apache-2.0 `main@829c6a56…`; Codebase Memory `qodana-action`. **Question:** Docs rot when releases bump versions — how does this repo make stale docs FAIL CI?

## Regex-extract mentions from docs, assert equality against VERSION
**Path/Symbol:** `scan/__tests__/project.test.ts` — Azure README major-version check (:37-48), CircleCI orb exact-version check (:50-64), skipped action-README full-version check (:21-34, `test.skip`), commented-out task.json check (:35-44).
**Signature:** pattern `/ - task: QodanaScan@\d+/g` asserted equal to `QodanaScan@${VERSION.split('.')[0]}`; orb pattern `/\d+\.\d+\.\d+/g` each === VERSION.
**Data Shape:** VERSION imported from `common/qodana.ts` (= cli.json version) — single source of truth.

### Decisive source
```ts
const orbFileContent = fs.readFileSync(orbFile, 'utf8')
const mentions = orbFileContent.match(/\d+\.\d+\.\d+/g) || []
expect(mentions.length > 0).toEqual(true)   // also fails if NO mention found
for (const mention of mentions) {
  expect(mention).toEqual(VERSION)
}
```

**Flow:** on every test run, extract every version-looking token from the doc files → require ≥1 mention (guards against accidental removal too) → each must EQUAL the current release version exactly. Azure README pins only the MAJOR (task marketplace convention `QodanaScan@N`); the orb pins FULL semver (its inline curl installs that exact tag).
**Invariant:** "Zero mentions" is a FAILURE, not a pass — otherwise deleting docs would green the suite. Major-only vs full-pin choice follows the consumer's resolution semantics (Azure tasks resolve by major, CircleCI orbs by full tag).
**Probe:** `scan/__tests__/project.test.ts` — active doc-consistency tests: Azure Pipelines README major-version :58-68 and CircleCI orb+example exact-equality :70-87 (the action-README check at :36 is `test.skip`, the task.json twin is commented out — NOT runnable verbatim as previously pinned :21-64); plus the live-download checksum sweep :90-107 over all six platform_arch combos (`SUPPORTED_PLATFORMS = ['windows','linux','darwin']`, `SUPPORTED_ARCHS = ['x86_64','arm64']`, common/qodana.ts:30-31) asserting cli.json agreement.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qodana-action", query: "README orb version mentions latest", limit: 6 });
```

## Verdict
Adopt doc-as-test version pinning for any released artifact whose docs embed copy-paste snippets; adapt regex strictness to your consumers' version-resolution rules; note the deliberate skips (action-README check disabled upstream — don't cargo-cult its regex without re-enabling intent).
