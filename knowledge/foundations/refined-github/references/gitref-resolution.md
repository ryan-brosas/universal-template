<!-- capsule-v2 -->
# Git-Ref Resolution Ladder — how do you determine the current branch/ref on a page that may not have a branch picker?

**Source:** refined-github MIT `main@3bbe6088fe301d0d5cf1ae751a49307005762a68`; Codebase Memory `refined-github`. **Question:** What is the ordered evidence chain for the current git ref, and why must it stay synchronous?

## Connected graph-selected seam
**Path/Symbol:** `source/github-helpers/get-current-git-ref.ts:` `getCurrentGitRef` (:66–86 of file), `getGitRef` (:16–40), `getCurrentBranchFromFeed` (:43–58); title/branch extraction `source/github-helpers/index.ts:extractCurrentBranchFromBranchPicker` (:159–163).
**Signature:** `getCurrentGitRef(): string | undefined`; `getGitRef(pathname: string, title: string): string | undefined`.
**Data Shape:** applicable route types gated by set `{tree, blob, blame, edit, commit, commits, compare}`; slashed branches are THE ambiguity throughout.

### Decisive source
```ts
// Ladder, in order:
const refViaPicker = picker && extractCurrentBranchFromBranchPicker(picker);
if (refViaPicker) return refViaPicker;
// Slashed branches on commits pages (incl. no picker): parse the atom feed URL
const branchFromFeed = getCurrentBranchFromFeed();  // pathname.slice(4).join('/').replace(/\.atom$/,'')
// Last resort: first path segment after /user/repo/<type>/ — may be wrong for slashed refs
return getGitRef(location.pathname, document.title);
```
```ts
// The picker itself hides clipped names in @title:
return branchPicker.title === 'Switch branches or tags'
	? branchPicker.textContent.trim()   // full name shown
	: branchPicker.title;               // name was clipped → placed in title attribute
```

**Flow:** DOM picker (authoritative) → atom-feed link (`link[type="application/atom+xml"]`, only on commit lists; missing-after-AJAX tolerated silently) → pure-function fallback parsing `pathname + document.title` via `/ at (?<branch>[\w\-./]+)(?: · repo)?$/i`. Feed errors and missing pickers return `undefined` rather than throwing.
**Invariant:** "Must not be async because it's used by GitHubFileURL. May return different results depending on whether it's called before or after DOM ready" (:15, :59) — porters adding an `await elementReady()` here break every synchronous URL algebra built on top. The pure fallback can MISPARSE slashed branches on non-commits pages (documented tradeoff, not a bug); callers needing certainty must use the DOM-dependent path.
**Probe:** `source/github-helpers/get-current-git-ref.test.ts:getCurrentGitRef` (:158–178) pins all three tiers incl. `this/branch/has/many/slashes`; `getGitRef` table-driven test :17–155 covers type-gating and title parsing.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", query: "getCurrentGitRef getGitRef branchSelector feed", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ladder pattern (authoritative-DOM → derived-artifact → pure-parse) for any "current entity" resolution under partial-render conditions. Adapt selectors/feed markers to your host. Keep it synchronous or push the sync requirement up deliberately. Direct tests present.
