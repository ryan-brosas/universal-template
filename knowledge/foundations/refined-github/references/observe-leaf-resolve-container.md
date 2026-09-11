<!-- capsule-v2 -->
# Observe-Leaf-Resolve-Container — how do you survive GitHub's class-hash churn when the stable element is an ancestor of what you can select?
**Source:** refined-github MIT `main@3187161079033cc1eda1731044ba8a2fdd7b69b4`; Codebase Memory `refined-github`. **Question:** When upstream renames hashed CSS-module classes on a parent, do you re-anchor your selector or move resolution into the callback?

## Connected graph-selected seam
**Path/Symbol:** `source/features/clean-conversation-headers.tsx:` `init` (:124–130), `cleanPrHeader` (:93–122); fix commit `3187161` (#9957) — observe target moved from the summary row to the leaf branch-name node, container resolved with `closestElement`.
**Signature:** `cleanPrHeader(headRef: HTMLElement): Promise<void>` (was `(summaryRow: HTMLElement)`); `closestElement(selector, context): Element | undefined` from `select-dom`.
**Data Shape:** observe selector `'…[class^="PullRequestBranchName"] ~ div [class^="PullRequestBranchName"]'` matches a DESCENDANT branch-name node; `closestElement('.d-flex[class*="PullRequestHeaderSummary"]', headRef)` walks UP to the row that owns layout classes.

### Decisive source
```ts
async function cleanPrHeader(headRef: HTMLElement): Promise<void> {
	const summaryRow = closestElement('.d-flex[class*="PullRequestHeaderSummary"]', headRef);
	summaryRow.classList.add('rgh-clean-conversation-headers');
	...
}
// init:
observe(
	'[class^="PullRequestBranchName"] ~ div [class^="PullRequestBranchName"]',
	cleanPrHeader,
	{signal},
);
```

**Flow:** observer fires on the leaf branch-name node → one upward hop to the structural summary row → the rest of the pipeline (`isStickyHeader`, base extraction via `parseReferenceRaw`, fire-and-forget `void` legs) is UNCHANGED and still receives `summaryRow`. The PR-header fix (#9957) changed ONLY the two anchor points: where observation lands and where the working handle is derived.
**Invariant:** Anchor the observer at the most-stable leaf (a `[class^=…]` prefix that survives sibling churn), derive the mutable ancestor inside the callback via `closestElement`, and keep every downstream consumer signature-compatible. Never widen the observed selector to include the hashed ancestor itself — that is exactly what broke here. The `~ div` combinator encodes "the head branch sits in a later sibling div than the base" — it distinguishes head from base without reading content.
**Probe:** No unit test exists for this browser-bound feature (standing helper-only test caveat). Deterministic anchors at pin 3187161: `grep -cF 'closestElement(' source/features/clean-conversation-headers.tsx` = 1 (the single hop); `grep -oF '[class^="PullRequestBranchName"]' source/features/clean-conversation-headers.tsx | wc -l` = 3 across 2 lines (twice inside the observe selector, once as the `$()` base lookup); ROLE-INVERSION proof that the diff moved only the anchor: pre-pin `git show 3bbe6088:… | sed -n '/async function init/,/^}/p' | grep -cF '.d-flex[class*="PullRequestHeaderSummary"]'` = 1 (the row selector WAS the observe target), while at HEAD the same pattern survives on exactly 1 line — now the `closestElement` ARGUMENT inside `cleanPrHeader`, no longer in `init`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", query: "closestElement summaryRow cleanPrHeader", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the pattern: observe-leaf → resolve-container → unchanged downstream pipeline — it is the general defense against CSS-module hash drift on any SPA overlay, and this commit is its minimal real-world demonstration. Adapt selectors per host page. Omit nothing; the diff itself is the lesson. Coverage caveat: verified by deterministic anchors + live graph resolution against the fresh index; no unit runner exists for feature files.
