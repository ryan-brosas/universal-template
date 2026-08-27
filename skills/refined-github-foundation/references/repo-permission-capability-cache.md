<!-- capsule-v2 -->
# repo-permission-capability-cache — how do you expose permission capabilities without over-promising?

**Source:** refined-github MIT `main@3187161079033cc1eda1731044ba8a2fdd7b69b4`; Codebase Memory `refined-github`. **Question:** Features need "can this user do X in this repo" (admin / push / moderate). The authoritative answer is one GraphQL enum, but it needs a token and a network round-trip, and the DOM already shows permission hints. How do you cache the enum once per repo, fail closed, and still add a DOM fast-path that does not lie about what it proves?

## One cached enum with a fail-closed ladder
**Path/Symbol:** `source/github-helpers/get-user-permission.ts` — `getViewerPermission` :23–43, `viewerPermission` CachedFunction :45–48.
**Signature:** `getViewerPermission(): Promise<RepositoryPermission>` where `RepositoryPermission = 'ADMIN' | 'MAINTAIN' | 'READ' | 'TRIAGE' | 'WRITE'` (:21); `viewerPermission: CachedFunction` keyed by repo.

### Decisive source
```ts
async function getViewerPermission(): Promise<RepositoryPermission> {
	if (getRepo() === null) {
		throw new Error('This can only be called on a repository page');
	}

	if (!await hasToken()) {
		return 'READ';
	}

	try {
		const {repository} = await api.v4(`
			repository() {
				viewerPermission
			}
		`);

		return repository.viewerPermission;
	} catch {
		return 'READ';
	}
}

const viewerPermission = new CachedFunction('viewer-permission', {
	updater: getViewerPermission,
	cacheKey: () => getRepo()?.nameWithOwner ?? '',
});
```

**Flow:** three-way fail-closed ladder — throw when called off a repo page (programmer error, must be loud), downgrade to `'READ'` when there is no token (anonymous can at most read), downgrade to `'READ'` on ANY API error (catch-all: rate limit, network, auth) → the result is cached per repo via `cacheKey: () => getRepo()?.nameWithOwner ?? ''`, so navigating between repos re-fetches but revisiting a repo is free.
**Invariant:** (1) every failure mode lands on the LOWEST permission — a port that falls back to 'WRITE' on error would silently unlock destructive features for broken tokens; (2) the cache key is the repo, not the page — the value is repo-scoped by definition; (3) the enum values are documented inline from the GitHub docs (comment block :6–19) because MAINTAIN/TRIAGE are non-obvious; (4) cached `v4` here vs `v4uncached` in conversation-lock-resolution-ladder.md — freshness policy is per-fact.
**Probe:** executed pins: `grep -n "This can only be called on a repository page" source/github-helpers/get-user-permission.ts` → line 25; `grep -n "return 'READ'" source/github-helpers/get-user-permission.ts` → lines 29, 41; `grep -n "cacheKey" source/github-helpers/get-user-permission.ts` → line 47.

## Three predicates over one cache — including a deliberately uncacheable DOM fast-path
**Path/Symbol:** `source/github-helpers/get-user-permission.ts` — `userIsAdmin` :50–53, `userHasPushAccess` :56–59, `userIsModerator` :62–80.
**Signature:** each `(): Promise<boolean>`.

### Decisive source
```ts
export async function userIsAdmin(): Promise<boolean> {
	const repoAccess = await viewerPermission.get();
	return repoAccess === 'ADMIN';
}

/** Check if the user has complete write access to the repo (but no access to the repo Settings) */
export async function userHasPushAccess(): Promise<boolean> {
	const repoAccess = await viewerPermission.get();
	return repoAccess !== 'READ' && repoAccess !== 'TRIAGE';
}

/** Check if the user can edit all comments and comment on locked issues on the current repo */
export async function userIsModerator(): Promise<boolean> {
	// Faster DOM-based check, if the DOM is available.
	// This cannot be cached in `viewerPermission` because it guarantees you have *at least* moderation access, but can't tell if you have *more* capabilities
	const hasPermissionsViaDom = elementExists([
		'.lock-toggle-link > .octicon-lock',
		'[aria-label^="You have been invited to collaborate"]',
		'[title^="You are a member"]',
		'[title^="You are a maintainer"]',
		'[title^="You are a collaborator"]',
		// Don't check for admin access here. If the user has admin access, the DOM check in `viewerPermission` will use the DOM and be cached anyway
	]);

	if (hasPermissionsViaDom) {
		return true;
	}

	const repoAccess = await viewerPermission.get();
	return repoAccess !== 'READ';
}
```

**Flow:** admin/push are pure enum comparisons over the shared cache → moderator adds a synchronous DOM fast-path FIRST: any of five "you have ≥ collaborator" UI markers present → return true without touching the cache/API; otherwise fall through to the enum (`!== 'READ'`).
**Invariant:** (1) the asymmetry is the whole design — the DOM markers prove *at least* moderation but not *more*, so the fast-path result CANNOT be written into `viewerPermission` (the comment says exactly this); caching it would over-promise to the other predicates; (2) admin indicators are deliberately ABSENT from the DOM list — an admin hits the cached path instead, which knows the full answer; (3) push-access excludes TRIAGE (triage can manage issues but not push) — the predicate encodes the permission matrix, not just "not read"; (4) the DOM check is sync (`elementExists`) so a logged-in moderator pays zero latency.
**Probe:** executed pins: `grep -n "This cannot be cached in" source/github-helpers/get-user-permission.ts` → line 64; `grep -n "Don't check for admin access here" source/github-helpers/get-user-permission.ts` → line 71. No direct unit test upstream (browser-bound). GRAPH ANOMALY: `trace_path inbound` reports userIsAdmin callers_total 0 and userHasPushAccess 2, but direct grep finds userIsAdmin used by quick-repo-deletion.tsx:122 and userHasPushAccess by 4 feature files (clear-pr-merge-commit-message, unreleased-commits, closing-remarks .tsx+.svelte) — svelte/tsx import edges under-counted; source wins.

## Consumers: capabilities as declarative run conditions
**Path/Symbol:** `source/features/quick-repo-deletion.tsx` :118–125, `source/features/closing-remarks.tsx` :71–76, `source/features/quick-comment-edit.tsx` :23, `source/features/netiquette.svelte` :55.

### Decisive source
```tsx
void features.add(import.meta.url, {
	asLongAs: [
		pageDetect.isRepoRoot,
		pageDetect.isForkedRepo,
		userIsAdmin,
		isRepoUnpopular,
	],
```
```tsx
	asLongAs: [
		pageDetect.isPRConversation,
		pageDetect.isOpenConversation,
		userHasPushAccess,
	],
```

**Flow:** capability checks plug directly into the run-condition algebra as async predicates (feature-loader-lifecycle.md) — quick-repo-deletion stacks page + fork + admin + popularity gates; closing-remarks' second registration catches a PR *while it is being merged* and gates on push access → quick-comment-edit uses the inline form (`!await userIsModerator()` inside a composite condition, plus a second await at :92 after the element appears) → netiquette.svelte renders the Svelte `{#await userIsModerator() then isModerator}` block, showing the same predicate works across both rendering planes.
**Invariant:** the helper exposes CAPABILITIES (booleans), never actions — features compose them into their own gate stacks; the same predicate serves TSX features and Svelte features unchanged.
**Probe:** executed pins: `grep -n "userIsAdmin" source/features/quick-repo-deletion.tsx` → lines 11, 122; `grep -n "userHasPushAccess" source/features/closing-remarks.tsx` → lines 9, 75; `grep -n "userIsModerator" source/features/quick-comment-edit.tsx` → lines 8, 23, 92; `grep -n "userIsModerator" source/features/netiquette.svelte` → lines 15, 55.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", query: "userIsAdmin userHasPushAccess userIsModerator getViewerPermission" });
// total: 4, all line-exact in get-user-permission.ts (23-43 / 50-53 / 56-59 / 62-80)
await mcp.codebase_memory.trace_path({ project: "refined-github", function_name: "userIsModerator", direction: "inbound" });
// callers_total: 2 (quick-comment-edit ×2 hops) — svelte consumer invisible to graph; grep finds netiquette.svelte too
await mcp.codebase_memory.get_code_snippet({ project: "refined-github", qualified_name: "refined-github.source.github-helpers.get-user-permission.userIsModerator" });
// served source byte-identical to checkout read @ pin 3187161
```
Executed 2026-08-29 @ pin 3187161 via vendor CLI (identical tool surface).

## Verdict
Adopt the one-cached-enum + fail-closed-ladder shape and the asymmetric-fast-path rule (a DOM hint may short-circuit a check only when its guarantee is a SUBSET of the check's, and then it must stay out of the cache). Adapt the enum values, selectors, and permission matrix to your host's roles. Omit the specific GitHub role names beyond the pattern. Coverage caveat: `no_recorded_issue` @ gen 2026-08-24T14:04:43Z on get-user-permission.ts + all four consumer files; no direct test upstream (browser-bound) — deterministic pins stand in; graph inbound traces under-count svelte/tsx consumers (recorded anomaly). Cross-reference: feature-loader-lifecycle.md (asLongAs algebra), api-graphql-wrapper.md (cached v4), dom-first-ttl-value-cache.md (sibling CachedFunction seam with TTL), token-identity-gate.md (hasToken plane).
