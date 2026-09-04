<!-- capsule-v2 -->
# conversation-lock-resolution-ladder — how do you resolve a host fact (is this conversation locked?) when each available source covers a different user state?

**Source:** refined-github MIT `main@3187161079033cc1eda1731044ba8a2fdd7b69b4`; Codebase Memory `refined-github`. **Question:** "Is this issue/PR locked" is answerable from three places — React preloaded data (initial load only), the DOM lock toggle (moderators only), the GraphQL API (token required) — and no single one works for every visitor. How do you combine them so the answer arrives as fast as possible without a token requirement?

## First-DEFINED-wins concurrent resolution
**Path/Symbol:** `source/github-helpers/is-conversation-locked.ts` — `isConversationLocked` :43–57 (+ `resolveIfDefined` closure :46–51).
**Signature:** `isConversationLocked(): Promise<boolean | undefined>` (default export).
**Data Shape:** resolves to the first non-undefined result of three concurrent checks; may never resolve when every defined-capable source is unavailable (see Invariant 3).

### Decisive source
```ts
export default async function isConversationLocked(): Promise<boolean | undefined> {
	// Like Promise.race, but it only resolves if the result is not undefined
	return new Promise(resolve => {
		const resolveIfDefined = async (check: () => Promise<boolean | undefined>): Promise<void> => {
			const isLocked = await check();
			if (isLocked !== undefined) {
				resolve(isLocked);
			}
		};

		void resolveIfDefined(isConversationLockedViaReactData);
		void resolveIfDefined(isConversationLockedViaDom);
		void resolveIfDefined(isConversationLockedViaApi);
	});
}
```

**Flow:** all three checks start concurrently (fire-and-forget `void` calls) → each returns `boolean | undefined`, where `undefined` means "my precondition failed, I can't answer" → the first DEFINED value settles the outer promise; later results are ignored (the promise is already settled).
**Invariant:** (1) this is NOT `Promise.race` — race would settle on the first RESOLVED value even if that value is undefined; the comment pins the distinction; (2) `undefined` is the load-bearing "I cannot answer" signal, distinct from `false` (definitely unlocked); (3) there is NO timeout anywhere — `elementReady` without a signal waits forever, so a state where every defined-capable source is unavailable (e.g. logged-out non-moderator after soft-nav with no preloaded data) stalls rather than resolving undefined. The consumer turns that stall into fail-closed behavior: as an `asLongAs` run condition, a never-resolving check simply means the feature never runs.

## The three sources and their disjoint preconditions
**Path/Symbol:** `source/github-helpers/is-conversation-locked.ts` — `isConversationLockedViaApi` :7–19, `isConversationLockedViaDom` :21–28, `isConversationLockedViaReactData` :30–41.
**Signature:** each `(): Promise<boolean | undefined>`.

### Decisive source
```ts
async function isConversationLockedViaApi(): Promise<boolean | undefined> {
	if (!await hasToken()) {
		return undefined;
	}
	const {repository} = await api.v4uncached(GetIssueLockStatus, {
		variables: {number: getConversationNumber()!},
	});
	return repository.issueOrPullRequest.locked;
}

async function isConversationLockedViaDom(): Promise<boolean | undefined> {
	// The form only appears to moderators
	const lockToggle = await elementReady([
		'.discussion-sidebar-item svg.octicon-key + strong', // PRs, old issues
		'[class^="Item__LiBox"]:has(svg.octicon-lock) [data-component="ActionList.Item--DividerContainer"] span', // Issues
	]);
	return lockToggle ? lockToggle.textContent === 'Unlock conversation' : undefined;
}

async function isConversationLockedViaReactData(): Promise<boolean | undefined> {
	if (!isInitialLoad()) {
		return;
	}
	const data = await elementReady('[data-target="react-app.embeddedData"]');
	return data
		? JSON.parse(data.textContent).payload?.preloadedQueries?.[0].result.data.repository?.issue?.locked
		: undefined;
}
```
```graphql
query GetIssueLockStatus($owner: String!, $name: String!, $number: Int!) {
	repository(owner: $owner, name: $name) {
		issueOrPullRequest(number: $number) {
			... on Lockable {
				locked
			}
		}
	}
}
```

**Flow:** API path bails to undefined without a token, else `v4uncached` (lock state must not be stale-cached) with the repo owner/name auto-injected by the wrapper and `... on Lockable` fragment spread because `issueOrPullRequest` is a union → DOM path awaits the lock TOGGLE (not the lock icon — the toggle text 'Unlock conversation' is the positive signal) with two selector generations (old `.discussion-sidebar-item` vs React `Item__LiBox`) → React-data path reads the page's embedded JSON (`preloadedQueries[0]`) but ONLY on initial load — after soft navigation the element is gone/stale, so it returns undefined immediately.
**Invariant:** (1) the preconditions are deliberately DISJOINT user states — token vs moderator-DOM vs initial-load — so their union covers every visitor class where the fact matters; (2) the DOM check reads the *toggle* text, which only moderators see — for everyone else it hangs (by design, per Invariant 3 above); (3) the API uses `v4uncached` while the permission plane (repo-permission-capability-cache.md) uses cached `v4` — freshness policy is per-fact, not global; (4) the GraphQL variables show the wrapper contract: caller supplies only `number`; `$owner`/`$name` are injected from route context (api-graphql-wrapper.md).
**Probe:** no direct unit test (browser-bound). Executed pins: `grep -n "Like Promise.race" source/github-helpers/is-conversation-locked.ts` → line 44; `grep -n "only appears to moderators" source/github-helpers/is-conversation-locked.ts` → line 24; `grep -n "on Lockable" source/github-helpers/is-conversation-locked.gql` → line 4.

## Consumer: run-condition gating on the resolved fact
**Path/Symbol:** `source/features/locked-issue.tsx` — registration :37–43.
**Signature:** `features.add(import.meta.url, {asLongAs: [...], init})`.

### Decisive source
```tsx
void features.add(import.meta.url, {
	asLongAs: [
		pageDetect.isConversation,
		async () => await isConversationLocked() ?? false,
	],
	init,
});
```

**Flow:** the resolved fact becomes a declarative run condition — `?? false` maps "never answered" to "feature off" at the GATE level (the inner promise may still hang; the gate just never passes) → `init` observes the state-label element and injects a "Locked" indicator next to it.
**Invariant:** the helper stays side-effect-free and returns `boolean | undefined`; the CONSUMER decides what undefined means (`?? false` here). A port should keep that split — resolution logic in the helper, policy in the feature.
**Probe:** executed pin: `grep -n "isConversationLocked() ?? false" source/features/locked-issue.tsx` → line 43. Live `trace_path inbound isConversationLocked` → callers_total 1 (locked-issue) — single consumer confirmed.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", query: "isConversationLocked" });
// total: 1 — refined-github.source.github-helpers.is-conversation-locked.isConversationLocked Function 43-57 (the three Via* helpers are module-local, not graph nodes — cited from direct read)
await mcp.codebase_memory.trace_path({ project: "refined-github", function_name: "isConversationLocked", direction: "inbound" });
// callers_total: 1 · locked-issue
await mcp.codebase_memory.get_code_snippet({ project: "refined-github", qualified_name: "refined-github.source.github-helpers.is-conversation-locked.isConversationLocked" });
// served source byte-identical to checkout read @ pin 3187161
```
Executed 2026-08-29 @ pin 3187161 via vendor CLI (identical tool surface).

## Verdict
Adopt the first-defined-wins concurrent resolution shape and the disjoint-precondition source design — host-agnostic mechanics for any fact that different user states can see through different channels. Keep the no-timeout property only if your consumer gates on the promise (fail-closed by non-resolution); otherwise add a timeout. Adapt the three sources themselves (React embedded-data shape, toggle selectors, GraphQL query) to your host. Omit the specific selectors and the `preloadedQueries[0]` JSON path — GitHub-private contracts. Coverage caveat: `no_recorded_issue` @ gen 2026-08-24T14:04:43Z on is-conversation-locked.ts/.gql + locked-issue.tsx; no direct test upstream (browser-bound) — deterministic pins stand in. Cross-reference: api-graphql-wrapper.md (variable injection, v4 vs v4uncached), feature-loader-lifecycle.md (asLongAs gating), gitref-resolution.md (another DOM-first host-fact ladder).
