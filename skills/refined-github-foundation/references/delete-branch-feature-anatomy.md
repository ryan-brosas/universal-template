<!-- capsule-v2 -->
# Delete-Branch Feature Anatomy — how does a minimal destructive-action feature compose the harness primitives end to end?

**Source:** refined-github MIT `main@3187161079033cc1eda1731044ba8a2fdd7b69b4`; Codebase Memory `refined-github`. **Question:** What is the complete contract for adding a token-gated destructive UI action — visibility gating, confirmation, API call shape, and post-success navigation?

## Connected graph-selected seam
**Path/Symbol:** `source/features/delete-branch.tsx:` `deleteBranch` (:15–23), `handleClickDeletion` (:25–36), `add` (:38–57), `init` (:59–64), registration (:66–72). NEW feature added at this pin (#9974); wired via one import in `source/refined-github.ts:221`.
**Signature:** `deleteBranch(branchName: string): Promise<void>`; `add(contributeContainer: HTMLElement): void`; `init(signal: AbortSignal): Promise<void>`.
**Data Shape:** API call `api.v3('git/refs/heads/' + encodeURIComponent(branchName), {method: 'DELETE', responseFormat: 'text'})` — repo-relative path algebra from `api-rest-wrapper`, text format because a 204 delete has no JSON body. Success side effect is a location change, not a return value.

### Decisive source
```ts
function add(contributeContainer: HTMLElement): void {
	if (elementExists([
		// No button if there are open PRs
		'a[class*="PullRequestLink-module"]',
		// No button if the branch is linked to upstream repo (generally the main branch)
		'.octicon-sync',
	], contributeContainer)) {
		return;
	}
	contributeContainer.prepend(
		<button type="button" className="btn btn-danger rgh-delete-branch"
			ref={withTooltipRef('Delete branch')}>
			<TrashIcon/>
		</button>,
	);
}

async function init(signal: AbortSignal): Promise<void> {
	// This bar does not appear on the default branch of the root repo, so no further checks are required
	// The element is empty if the user doesn't have push access
	observe('[data-testid="branch-info-bar"] > .d-flex.gap-2:not(:empty)', add, {signal});
	delegate('.rgh-delete-branch', 'click', handleClickDeletion, {signal});
}

void features.add(import.meta.url, {asLongAs: [pageDetect.isRepoRoot], requiresToken: true, init});
```

**Flow:** `selector-observer` fires once per soft-nav on the branch-info bar → `add()` re-checks two EXCLUSION selectors inside the container (open-PR link present OR upstream-sync icon present ⇒ no button) → prepend danger button (caller-ID dedupe comes free via the `rgh-*` class) → click → `confirm()` native dialog → `getCurrentGitRef()` supplies the branch name synchronously → `showToast(async () => deleteBranch(...))` wraps the DELETE with progress/done messages → redirect to `buildRepoUrl('activity?activity_type=branch_deletion')`.
**Invariant:** Four independent gates stack and each covers a different failure mode: `requiresToken: true` (write needs auth), `asLongAs: [isRepoRoot]` + the comment-documented absence of the bar on the default branch of the root repo (default-branch protection comes from GitHub's own UI, not local logic), `:not(:empty)` on the observed container (empty ⇒ no push access), and the two exclusion selectors (deleting a branch with open PRs / an upstream-linked branch breaks things). A porter who collapses these into one check loses permission handling or default-branch safety. The branch name MUST go through `encodeURIComponent` before path interpolation (slashed branches).
**Probe:** No unit test exists (browser-bound feature — standing caveat: unit tests cover pure helpers only). Deterministic anchors: `grep -c 'rgh-delete-branch' source/features/delete-branch.tsx` = 2; `grep -c 'git/refs/heads' source/features/delete-branch.tsx` = 1; the Test-URL trailer (:74–82) holds EXACTLY 5 fixture URLs (`sed -n '74,82p' source/features/delete-branch.tsx | grep -c 'https://github.com'` = 5) — deletable branch, default branch, open PR, open PR on fork, lacking permissions.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", query: "deleteBranch branch deletion contributeContainer", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-gate stacking order (token → route predicate → container emptiness → content exclusions), the confirm→toast→DELETE→redirect sequencing, and `encodeURIComponent` before ref-path interpolation — they generalize to any destructive SPA overlay action. Adapt selectors (`data-testid="branch-info-bar"`, `PullRequestLink-module`, `octicon-sync`), copy, and the activity-page redirect target to your host. Omit nothing portable; the whole feature is 83 lines and every line carries a reusable decision. Coverage caveat: browser-bound, verified by deterministic anchors + live graph resolution, not by unit test.
