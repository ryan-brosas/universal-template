<!-- capsule-v2 -->
# dom-first-ttl-value-cache — how do you cache a repo-scoped value cheaply when the DOM already shows it on some pages?

**Source:** refined-github MIT `main@3187161079033cc1eda1731044ba8a2fdd7b69b4`; Codebase Memory `refined-github`. **Question:** "What is this repo's default branch?" is needed by ~10 features. The API answers it, but on the repo root page the DOM ALREADY shows it (the branch picker). How do you get a zero-request answer where the DOM is authoritative, an API answer elsewhere, and a free answer on revisits?

## DOM-first, API-fallback updater inside a TTL cache
**Path/Symbol:** `source/github-helpers/get-default-branch.ts` — `fromDom` :11–27, `fromApi` :29–40, `defaultBranchOfRepo` :42–57, `getDefaultBranch` :58–60.
**Signature:** `getDefaultBranch(): Promise<string>` (default export); `defaultBranchOfRepo: CachedFunction` with `maxAge: {hours: 1}`, `staleWhileRevalidate: {days: 20}`.

### Decisive source
```ts
// Do not make this function complicated. We're only optimizing for the repo root.
async function fromDom(): Promise<string | undefined> {
	if (!['', 'commits'].includes(getRepo()!.path)) {
		return;
	}

	// We're on the default branch, so we can extract it from the current page. This exclusively happens on the exact pages:
	// /user/repo
	// /user/repo/commits (without further path)
	const element = await elementReady(branchSelector);

	if (!element) {
		return;
	}

	return extractCurrentBranchFromBranchPicker(element);
}

export const defaultBranchOfRepo = new CachedFunction('default-branch', {
	// DO NOT use optional arguments/defaults in "cached functions" because they can't be memoized effectively
	// https://github.com/sindresorhus/eslint-plugin-unicorn/issues/1864
	async updater(repository: NameWithOwner): Promise<string> {
		if (!repository) {
			throw new Error('getDefaultBranch was called on a non-repository page');
		}

		// eslint-disable-next-line @typescript-eslint/prefer-nullish-coalescing -- Wrong, type can be `false`
		return (isCurrentRepo(repository) && await fromDom()) || fromApi(repository);
	},

	maxAge: {hours: 1},
	staleWhileRevalidate: {days: 20},
});

export default async function getDefaultBranch(): Promise<string> {
	return defaultBranchOfRepo.get(getRepo()!.nameWithOwner);
}
```

**Flow:** the updater takes the repo as an EXPLICIT argument (no optional params — pinned comment links the eslint issue) → throws on non-repo pages → `(isCurrentRepo(repository) && await fromDom()) || fromApi(repository)`: DOM extraction is attempted ONLY when (a) the cached value's repo IS the current repo and (b) the current path is exactly '' or 'commits' — the two pages where "the branch shown" provably equals the default branch → otherwise the GraphQL `defaultBranchRef.name` query → result cached per-repo for 1h fresh / 20d stale-while-revalidate.
**Invariant:** (1) the DOM fast-path is scoped to pages where the DOM is AUTHORITATIVE (root/commits show the default branch by construction) — reading the branch picker on `/tree/<other-branch>` would cache a wrong value; the scope comment ("We're only optimizing for the repo root") is the guard; (2) `isCurrentRepo` prevents caching a DOM read of repo A under repo B's key during soft-nav races; (3) the `||` chain means any falsy DOM result (undefined element, non-root path) silently falls through to the API — no error surface; (4) the no-optional-arguments rule exists because argument defaults break the library's memoization keying; (5) SWR at 20 days means a stale-but-present value never blocks a feature while revalidating in the background.
**Probe:** executed pins: `grep -n "Do not make this function complicated" source/github-helpers/get-default-branch.ts` → line 12; `grep -n "DO NOT use optional arguments" source/github-helpers/get-default-branch.ts` → line 43; `grep -n "maxAge" source/github-helpers/get-default-branch.ts` → line 54; `grep -n "isCurrentRepo(repository) && await fromDom" source/github-helpers/get-default-branch.ts` → line 51. No direct unit test upstream (browser-bound).

## Path-segment algebra on top: "am I on the default branch?"
**Path/Symbol:** `source/github-helpers/is-default-branch.ts` — `isDefaultBranch` :5–28.
**Signature:** `isDefaultBranch(): Promise<boolean>` (default export).

### Decisive source
```ts
export default async function isDefaultBranch(): Promise<boolean> {
	const repo = getRepo();
	if (!repo) {
		// Like /settings/repositories
		return false;
	}

	const [type, ...parts] = repo.path.split('/');
	if (parts.length === 0) {
		// Exactly /user/repo, which is on the default branch
		return true;
	}

	if (!['tree', 'blob', 'commits'].includes(type)) {
		// Like /user/repo/pulls
		return false;
	}

	// Don't use `getCurrentGitRef` because it requires too much DOM. This is good enough, it only fails when:
	// defaultBranch === 'a/b' && currentBranch === 'a'
	const path = parts.join('/');
	const defaultBranch = await getDefaultBranch();
	return path === defaultBranch || path.startsWith(`${defaultBranch}/`);
}
```

**Flow:** pure URL algebra first (free): no repo context → false; bare `/user/repo` → true without any async work; non-file route types (`pulls`, `issues`, …) → false → only then consult the cached default branch and compare with PREFIX semantics (`path === branch || path.startsWith(branch + '/')`) so `/tree/main/subdir` counts as on-default-branch.
**Invariant:** (1) the sync short-circuits come BEFORE the async lookup — the common cases never touch the cache; (2) the prefix match deliberately uses `${defaultBranch}/` (slash-terminated) so branch `main` does not match path `mainline`; (3) the known-failure case is documented inline ("it only fails when: defaultBranch === 'a/b' && currentBranch === 'a'") — on branch 'a', a URL like `/tree/a/b/subdir` yields path 'a/b/subdir', which `startsWith('a/b/')` accepts as on-default-branch even though the user is on branch 'a' with a directory named 'b'; the prefix test cannot distinguish branch-name prefixes from directory prefixes, and the author accepted that collision rather than paying for DOM ref extraction; (4) `getCurrentGitRef` (DOM ref extraction) was rejected as "too much DOM" — URL algebra + one cached value beats DOM scraping here.
**Probe:** executed pins: `grep -n "Don't use \`getCurrentGitRef\`" source/github-helpers/is-default-branch.ts` → line 23; `grep -n "startsWith" source/github-helpers/is-default-branch.ts` → line 27. No direct unit test upstream. GRAPH ANOMALY: `trace_path inbound isDefaultBranch` reports callers_total 0; direct grep finds 3 consumers (unreleased-commits, default-branch-button, list-prs-for-branch) — default-import edges under-counted; source wins.

## Consumer: the value feeds both URLs and run conditions
**Path/Symbol:** `source/features/default-branch-button.tsx` — `getUrl` :24–35, registration :93–101.

### Decisive source
```tsx
const getUrl = memoize(async (currentUrl: string): Promise<string> => {
	const defaultUrl = new GitHubFileUrl(currentUrl);
	if (pageDetect.isRepoRoot()) {
		defaultUrl.route = '';
		defaultUrl.branch = '';
	} else {
		defaultUrl.branch = await getDefaultBranch();
	}
	return defaultUrl.href;
});
```
```tsx
void features.add(import.meta.url, {
	include: [pageDetect.isRepoTree, pageDetect.isSingleFile, isRepoCommitListRoot],
	exclude: [isDefaultBranch],
	requiresToken: true,
	init,
});
```

**Flow:** the same cached value builds the "view on default branch" link (GitHubFileUrl five-field algebra, github-file-url.md) AND negates itself as an `exclude:` run condition — the button hides exactly when you are already on the default branch → the link re-resolves on mouseenter because "the URL may change without a DOM refresh" (issue #6554 comment).
**Invariant:** one cached value serves two different consumption shapes (URL construction + boolean gate) without either consumer knowing about the other — the cache is the seam.
**Probe:** executed pins: `grep -n "isDefaultBranch" source/features/default-branch-button.tsx` → lines 14, 97; `grep -n "Update on hover because the URL may change" source/features/default-branch-button.tsx` → line 70. Fan-in: live `trace_path inbound getDefaultBranch` → callers_total 14; direct grep → 10 feature files + is-default-branch.ts.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", query: "getDefaultBranch defaultBranchOfRepo isDefaultBranch extractCurrentBranchFromBranchPicker" });
// total: 3 (+extractCurrentBranchFromBranchPicker in index.ts 161-165, already cited by route-context-url-algebra.md)
await mcp.codebase_memory.trace_path({ project: "refined-github", function_name: "getDefaultBranch", direction: "inbound" });
// callers_total: 14 (clean-conversation-headers ×3, clear-pr-merge-commit-message ×3, comments-time-machine-links, default-branch-button, …)
await mcp.codebase_memory.get_code_snippet({ project: "refined-github", qualified_name: "refined-github.source.github-helpers.get-default-branch.getDefaultBranch" });
// served source byte-identical to checkout read @ pin 3187161
```
Executed 2026-08-29 @ pin 3187161 via vendor CLI (identical tool surface).

## Verdict
Adopt the DOM-first/API-fallback/TTL-cached shape with its three guards (authoritative-page scoping, current-repo check, explicit-argument updater) and the prefix-terminated branch comparison — host-agnostic caching mechanics for any value the host UI already displays on specific routes. Adapt the authoritative-page set, the TTLs, and the route grammar. Omit the GitHub-specific selectors and query. Coverage caveat: `no_recorded_issue` @ gen 2026-08-24T14:04:43Z on get-default-branch.ts, is-default-branch.ts, default-branch-button.tsx, index.ts; no direct tests upstream (browser-bound) — deterministic pins stand in; graph inbound trace under-counts default-import consumers (recorded anomaly). Cross-reference: api-graphql-wrapper.md (query wrapping), repo-permission-capability-cache.md (sibling CachedFunction seam — capability vs value), route-context-url-algebra.md (extractCurrentBranchFromBranchPicker lives in that file), github-file-url.md (consumer URL algebra), run-conditions.md (exclude: gating).
