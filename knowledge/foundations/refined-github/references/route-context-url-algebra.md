<!-- capsule-v2 -->
# route-context-url-algebra — how do you derive route context (conversation number, repo URLs, tag versions) from a soft-navigating SPA's URL bar without a router?

**Source:** refined-github MIT `main@3187161079033cc1eda1731044ba8a2fdd7b69b4`; Codebase Memory `refined-github`. **Question:** The host SPA never exposes route state — every feature needs "which conversation am I on", "build me a URL in this repo", and "which tag is newest". How do you derive all of that from `location` alone, with the failure boundaries pinned by tests?

## Pathname-split conversation number with a hard split limit
**Path/Symbol:** `source/github-helpers/index.ts` — `getConversationNumber` :16–19.
**Signature:** `getConversationNumber(): number | undefined`.
**Data Shape:** reads `location.pathname` only; returns the numeric PR/issue number or `undefined` for every non-conversation route.

### Decisive source
```ts
export function getConversationNumber(): number | undefined {
	const [, _owner, _repo, type, prNumber] = location.pathname.split('/', 5);
	return (type === 'pull' || type === 'issues') && Number(prNumber) ? Number(prNumber) : undefined;
}
```

**Flow:** pathname is split with LIMIT 5 so deep sub-routes (`/pull/148/commits/<sha>`) still expose segment 4 as the number → the segment-3 gate (`pull`|`issues`) rejects `/commit/…`, `/tree/…`, `/compare/…`, bare `/issues`, and non-GitHub origins → `Number(prNumber)` guards non-numeric segments.
**Invariant:** (1) the split limit of 5 is load-bearing — without it `/pull/148/commits/<sha>` still works but any longer path would shift segments; (2) both gates are required: `type` membership alone would accept `/issues/anything`, `Number()` alone would accept `/commit/57bf4`-style numerics; (3) `undefined` (not 0/NaN) is the "not a conversation" signal — callers use it in `??`/falsy positions.
**Probe:** `source/github-helpers/index.test.ts` — `getConversationNumber` test pins 15 URL→result pairs including `/pull/148/commits/0019603…` → 148, `/pull/148/commits` → 148, `/commit/57bf4` → undefined, `gist.github.com/` → undefined, `/issues` → undefined. Read in full this pass; NOT executed (standing runner block).

## Slash-validating repo URL builder
**Path/Symbol:** `source/github-helpers/index.ts` — `buildRepoUrl` :23–33.
**Signature:** `buildRepoUrl<S extends string>(...pathParts: RequireAtLeastOne<Array<UnslashedString<S> | number>, 0>): string`.

### Decisive source
```ts
	for (const part of pathParts) {
		if (typeof part === 'string' && /^\/|\/$/.test(part)) {
			throw new TypeError('The path parts shouldn’t start or end with a slash: ' + part);
		}
	}

	return [location.origin, getRepo()?.nameWithOwner, ...pathParts].join('/');
```

**Flow:** runtime validation throws TypeError on any string part starting/ending with '/' BEFORE joining → `[location.origin, getRepo()?.nameWithOwner, ...parts].join('/')` builds an absolute URL rooted at the CURRENT repo (no owner/repo argument needed).
**Invariant:** the same no-slash rule exists at BOTH levels — type-level (`UnslashedString<S>` template-literal type + `RequireAtLeastOne`) and runtime (TypeError) — so a port that keeps only one level loses either compile-time safety or protection against untyped callers. 45 call sites rely on the current-repo rooting.
**Probe:** no direct unit test for buildRepoUrl itself; behavior pinned by its 45 consumers (live `trace_path inbound buildRepoUrl` → callers_total 45). Executed pin: `grep -n "shouldn’t start or end with a slash" source/github-helpers/index.ts` → line 28.

## Last-'@' tag parsing and version-tag ladders
**Path/Symbol:** `source/github-helpers/index.ts` — `parseTag` :41–44, `getLatestVersionTag` :64–85 (+ module regexes :62–63).
**Signature:** `parseTag(tag: string): {version: string; namespace: string}`; `getLatestVersionTag(tags: string[]): string`.

### Decisive source
```ts
export function parseTag(tag: string): {version: string; namespace: string} {
	const {namespace = '', version = ''} = /(?:(?<namespace>.*)@)?(?<version>[^@]+)/.exec(tag)?.groups ?? {};
	return {namespace, version};
}
```
```ts
const validVersion = /^[rv]?\d+(?:\.\d+)+/;
const isPrerelease = /^[rv]?\d+(?:\.\d+)+-\d/;
export function getLatestVersionTag(tags: string[]): string {
	// Some tags aren't valid versions; comparison is meaningless.
	// Just use the latest tag returned by the API (reverse chronologically-sorted list)
	if (tags.some(tag => !validVersion.test(tag))) {
		return tags[0];
	}

	// Exclude pre-releases
	let releases = tags.filter(tag => !isPrerelease.test(tag));
	if (releases.length === 0) { // They were all pre-releases; undo.
		releases = tags;
	}
	// …linear compareVersions max over releases
```

**Flow:** parseTag splits on the LAST '@' (greedy namespace group) so namespaces may themselves contain '@' → getLatestVersionTag runs three failure ladders IN ORDER: any non-version tag short-circuits to `tags[0]` (API list is reverse-chronological, so first IS latest-by-date), then prereleases (`-\d` suffix) are filtered out, and if ALL were prereleases the filter is UNDONE rather than returning nothing → linear max via `compareVersions`.
**Invariant:** (1) the short-circuit must come FIRST — comparing mixed garbage tags is meaningless and the comment says so; (2) the all-prerelease undo means the function never returns empty for a non-empty input; (3) `r`/`v` prefixes are tolerated by both regexes.
**Probe:** `index.test.ts` — `parseTag` pins 6 cases incl. `'@hi/you@1.2.3'` → `{namespace:'@hi/you', version:'1.2.3'}`; `getLatestVersionTag` pins 3 cases: version sort ('3.0' wins over 'v1.1'/'r2.0'), prerelease exclusion ('v2.0' wins over 'v2.1-0'), non-version short-circuit ('lol v0.0.0' returned as-is). Read in full; NOT executed (runner block).

## Asymmetric username/realname normalization
**Path/Symbol:** `source/github-helpers/index.ts` — `isUsernameAlreadyFullName` :46–60.
**Signature:** `isUsernameAlreadyFullName(username: string, realname: string): boolean`.

### Decisive source
```ts
	username = username.replaceAll('-', '').toLowerCase();
	realname = realname
		.normalize('NFD')
		// Remove diacritics, punctuation and spaces
		.replaceAll(/[\s\p{Diacritic}\p{Punctuation}]/gu, '')
		.toLowerCase();
	return username === realname;
```

**Flow:** username side strips only '-' and case; realname side NFD-normalizes then strips ALL whitespace/diacritics/punctuation (unicode-property classes with the `u` flag) → equality test.
**Invariant:** the asymmetry is deliberate — usernames never contain spaces/diacritics, realnames do. Test-pinned edges: `'nicolo'` == `'Nicolò'` (diacritic stripped) but `'chipwolf'` != `'Chip Wolf ‮ '` (the RLE format character U+202E is NOT in `\p{Punctuation}`, so it survives and breaks equality). A port that uses `\W` instead of the property classes changes which exotic characters survive.
**Probe:** `index.test.ts` — 9 true/false pairs incl. both edges above. Read in full; NOT executed (runner block).

## Poking the host's own socket layer + per-page memoized permalink check
**Path/Symbol:** `source/github-helpers/index.ts` — `triggerConversationUpdate` :175–183, `isPermalink` :97–108 (memo config :92–94).
**Signature:** `triggerConversationUpdate(): void`; `isPermalink: () => Promise<boolean>` (memoized per `location.pathname`).

### Decisive source
```ts
export function triggerConversationUpdate(): void {
	const marker = $('.js-timeline-marker');
	marker.dispatchEvent(
		new CustomEvent('socket:message', {
			bubbles: true,
			detail: {data: {gid: marker.dataset.gid}},
		}),
	);
}
```
```ts
export const isPermalink = mem(async () => {
	if (/^[\da-f]{40}$/.test(location.pathname.split('/', 5)[4])) {
		return true; // commit
	}
	// Awaiting only the branch selector means it resolves early even if the icon tag doesn't exist, whereas awaiting the icon tag would wait for the DOM ready event before resolving.
	return elementExists('.octicon-tag', await elementReady(branchSelector));
}, cachePerPage);
```

**Flow:** triggerConversationUpdate dispatches a BUBBLING `socket:message` CustomEvent carrying `{data:{gid}}` onto `.js-timeline-marker` — GitHub's own socket handler picks it up and refreshes the stale conversation (issue #2465 workaround; single consumer quick-review quickApprove) → isPermalink first tries the pure check (segment 5 is a 40-hex commit SHA), else awaits ONLY the branch selector becoming ready and then tests for the tag icon — the comment documents that awaiting the tag icon directly would block on DOM-ready even when the answer is already decidable.
**Invariant:** (1) the event name/detail shape (`socket:message` / `{data:{gid}}`) is a private host contract — adapt, don't assume; (2) isPermalink's memo key is `location.pathname` (cachePerPage :92–94), so it re-evaluates exactly on navigation; (3) the early-resolution ordering (selector-ready THEN icon-exists) is the whole point of the async shape.
**Probe:** no direct unit test (DOM-bound). Executed pins: `grep -n "socket:message" source/github-helpers/index.ts` → line 179; `grep -n "cacheKey" source/github-helpers/index.ts` → line 93. COVERAGE CAVEAT: `isPermalink` has NO graph node (mem-wrapped const arrow — search_graph total 0 for "isPermalink"); cited from direct source read only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", query: "getConversationNumber buildRepoUrl parseTag getLatestVersionTag isUsernameAlreadyFullName triggerConversationUpdate", mode: "ids" });
// total: 6, all in source/github-helpers/index.ts, line-exact (16-19 / 23-33 / 41-44 / 64-85 / 46-60 / 175-183)
await mcp.codebase_memory.trace_path({ project: "refined-github", function_name: "getConversationNumber", direction: "inbound" });
// callers_total: 24 · buildRepoUrl: 45 · getLatestVersionTag: 1 (unreleased-commits) · parseTag: 2 (tag-changes-link) · isUsernameAlreadyFullName: 1 (show-names) · triggerConversationUpdate: 1 (quick-review)
```
Executed 2026-08-28 @ pin 3187161 via vendor CLI (identical tool surface).

## Verdict
Adopt the limit-split pathname algebra, the dual-level (type+runtime) slash validation, the three-ladder version-tag selection, and the asymmetric normalization — all are host-agnostic URL/string mechanics with test-pinned boundaries. Adapt the segment positions, event name/detail shape, and selectors to your host's URL grammar and private contracts. Omit the RGH-self predicates (`isRefinedGitHubRepo` etc.) and `upperCaseFirst` (trivial). Coverage caveat: `no_recorded_issue` @ gen 2026-08-24T14:04:43Z on index.ts + index.test.ts; direct test read in full (33 assertions across 4 functions) but NOT executed (standing runner block); `isPermalink` graph-node absent — source-read citation. Cross-reference: gitref-resolution.md (branch-picker extraction from the same file), github-file-url.md (five-field URL algebra).
