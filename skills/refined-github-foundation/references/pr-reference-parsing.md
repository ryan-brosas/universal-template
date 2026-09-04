<!-- capsule-v2 -->
# PR Branch Reference Parsing — how do you extract head/base repo:branch from the PR UI across both old and new views?

**Source:** refined-github MIT `main@3bbe6088fe301d0d5cf1ae751a49307005762a68`; Codebase Memory `refined-github`. **Question:** What is the two-argument reference grammar and its validation contract?

## Connected graph-selected seam
**Path/Symbol:** `source/github-helpers/pr-branches.ts:` `parseReferenceRaw` (:31–56 of file), `parseReference` (:58–63), `getBranches` (:65–80).
**Signature:** `parseReferenceRaw(absolute: string, relative: string): PrReference`; `getBranches(): {base: PrReference; head: PrReference}` via lazy getters.
**Data Shape:** `PrReference = {absolute, relative, owner, name, branch, nameWithOwner}` — `absolute` is always `owner/repo:branch`; `relative` is what the UI displays: bare `branch` on same-repo PRs, `owner:branch` on cross-repo.

### Decisive source
```ts
const absoluteReferenceRegex = /^(?<nameWithOwner>(?<owner>[^/:]+)\/(?<name>[^:]+)):(?<branch>.+)$/;
// We must receive the relative reference because it also tells whether it's a cross-repo PR:
const expectedRelative = [branch, `${owner}:${branch}`];
if (!expectedRelative.includes(relative)) {
	throw new TypeError(`Expected \`relative\` to be either "${expectedRelative.join('" or "')}", got "${relative}"`);
}
```

**Flow:** DOM scrape (`[class*="PullRequestHeaderSummary"] a[class^="PullRequestBranchName"]` with `.base-ref`/`.head-ref` fallbacks marked for deletion after legacy view removal) → textContent pairs fed to the pure parser → regex splits absolute → cross-validation against relative → typed record out.
**Invariant:** BOTH arguments are required because `relative` encodes the cross-repo bit that `absolute` alone cannot disambiguate ("main" vs "fregante:main") — a porter accepting only absolute strings loses that distinction. The head element may not exist in old views (`$$optional(...)?.[1] ?? $('.head-ref')`), so getter access can throw `$()` ElementNotFoundError off-PR. Regex uses `[^/:]+ / [^:]+ / .+` so branches containing `/` or `:` survive.
**Probe:** `source/github-helpers/pr-branches.test.ts:6` pins `parseReferenceRaw('fregante/mem:main', 'main')` plus the TypeError paths for mismatched relative forms.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", query: "parseReferenceRaw getBranches PrReference base head", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the validated two-form parser for any VCS-UI scraping; adapt selectors per host layout. Omit legacy-view fallbacks once your target drops them (they carry explicit TODO dates). Direct test present.
