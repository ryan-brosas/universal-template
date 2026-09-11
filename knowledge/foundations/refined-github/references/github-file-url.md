<!-- capsule-v2 -->
# GitHubFileUrl Algebra — how do you rewrite one component of a repo-file URL when branch names can contain slashes?

**Source:** refined-github MIT `main@3bbe6088fe301d0d5cf1ae751a49307005762a68`; Codebase Memory `refined-github`. **Question:** How does the class split an ambiguous `/user/repo/tree/a/b/c` into (branch, filePath), and what is the mutation contract?

## Connected graph-selected seam
**Path/Symbol:** `source/github-helpers/github-file-url.ts:GitHubFileUrl` (:1–120+; Facade over internal URL per #3193).
**Signature:** `new GitHubFileUrl(url: string)`; fields `user/repository/route/branch/filePath`; `.assign(...Partial<GitHubFileUrl>): this`; getters/setters proxy everything else to the internal URL.
**Data Shape:** pathname = `'/' + [user, repository, route, branch, filePath].filter(Boolean).join('/')`.

### Decisive source
```ts
private disambiguateReference(ambiguousReference: string[]): {branch: string; filePath: string} {
	const branch = ambiguousReference[0];
	// History pages might use search parameters:
	const filePathFromSearch = this.searchParams.getAll('path[]').join('/');
	if (filePathFromSearch) { this.searchParams.delete('path[]'); return {branch, filePath: filePathFromSearch}; }
	const filePath = ambiguousReference.slice(1).join('/');
	// Only resolvable when BOTH the current ref and the candidate have slashes:
	if (!currentBranch || ambiguousReference.length === 1 || currentBranchSections.length === 1) {
		return {branch, filePath};
	}
	for (const [index, section] of currentBranchSections.entries()) {
		if (ambiguousReference[index] !== section) {
			console.warn(`The supplied path (...) is ambiguous (current reference is \`${currentBranch}\`)`);
			return {branch, filePath};   // first mismatch ⇒ default split
		}
	}
	return {branch: currentBranch, filePath: ambiguousReference.slice(currentBranchSections.length).join('/')};
}
```
```ts
// Repo roots carry everything after route in ONE field:
if (isRepoRoot(...)) return this.assign({user, repository, route, branch: ambiguousReference.join('/'), filePath: ''});
```

**Flow:** parse pathname (un-escaping `%2F`) → repo-root special case → else disambiguate: `path[]` search params win → single-segment refs can't be ambiguous → compare candidate segments against the CURRENT page's ref segments; full prefix match ⇒ adopt the multi-slash current branch and push remainder to filePath; any mismatch ⇒ warn + naive first-segment split.
**Invariant:** the ambiguity resolution DEPENDS ON GLOBAL PAGE STATE (`getCurrentGitRef()` reads DOM/title — issue #6637 tracks this debt): the same input string parses differently depending on the page it runs on. Porters unit-testing this class in isolation must reproduce that context or their expectations will diverge from production for slashed branches. Setter normalizes `%2F` before splitting or slashed branches encoded once get double-counted.
**Probe:** `source/github-helpers/github-file-url.test.ts` pins parse/assign/round-trip incl. nested objects and `get filePath from search` (:69); **the slash-disambiguation prefix-match path has NO direct test** — recorded as coverage caveat with source lines :21–62 as sole evidence.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", query: "GitHubFileUrl disambiguateReference assign pathname", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the five-field URL algebra + prefix-match disambiguation for any hierarchical-resource URL rewriter. Adapt field names/routes. Omit the global-state coupling only by making the current-ref an explicit constructor arg (recommended improvement when porting). Direct tests cover parsing/mutation; disambiguation caveat-recorded.
