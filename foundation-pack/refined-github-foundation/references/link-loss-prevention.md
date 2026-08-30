<!-- capsule-v2 -->
# prevent-link-loss — how do you rewrite raw host URLs pasted into a comment field into markdown links BEFORE submission destroys their context?

**Source:** refined-github MIT `main@3bbe6088fe301d0d5cf1ae751a49307005762a68`; Codebase Memory `refined-github`. **Question:** What is the URL→markdown rewriting contract for PR-commit, compare, and discussion links, and how does it avoid mangling links already inside markdown?

## Replacer-callback trio over location-anchored regexes
**Path/Symbol:** `source/github-helpers/prevent-link-loss.ts:preventPrCommitLinkLoss` / `preventPrCompareLinkLoss` / `preventDiscussionLinkLoss` / `avoidLinkLoss` (:14–96).
**Signature:** `avoidLinkLoss(field: HTMLTextAreaElement): void`; replacers match the native `String#replace` callback shape `(url, …groups, index, fullText): string`.
**Data Shape:** Regexes are built at module load with `location.origin` ESCAPED INTO the pattern (`escapeRegex` shim pending `RegExp.escape`; Safari <18.2 TODO) — they only match same-origin URLs. Flags `gi`.

### Decisive source
```ts
function preventPrCommitLinkLoss(url, repoNameWithOwner, pr, commit, commit2, index, fullText) {
	if (fullText[index + url.length] === ')') {
		return url; // already inside a markdown link — don't touch
	}
	const currentPr = getConversationNumber();
	const prReference = currentPr && Number(pr) === currentPr ? '(this PR)' : `(#${pr})`;
	const commitReference = commit2 ? `${commit}..${commit2}` : commit;
	return `[${getRepoReference(getRepo(), repoNameWithOwner, '@')}\\`${commitReference}\\` ${prReference}](${url})`;
}
```
with the shared reference rule:
```ts
const getRepoReference = (currentRepo, repoNameWithOwner, delimiter = '') =>
	repoNameWithOwner === currentRepo!.nameWithOwner ? '' : repoNameWithOwner + delimiter;
```

**Flow:** on field edit (`replaceFieldText` from `text-field-edit` preserves undo history) → each regex rewrites bare URLs into `[repo@`sha` (#123)](url)` style markdown; the char AFTER the match decides everything: if it's `)` the URL is already a markdown target and is returned untouched.
**Invariant:** (1) The paren-lookahead via `fullText[index + url.length]` — NOT a negative lookbehind — is what makes the transform idempotent; (2) cross-repo links keep an `owner/repo@` prefix while same-repo links DROP it entirely (empty string), matching GitHub's own autolink style; (3) within the current conversation the PR number renders as `(this PR)`; (4) compare links carry the `#diff-…` anchor truncated to 16 chars in label position.
**Probe:** `source/github-helpers/prevent-link-loss.test.ts:24–170+`: non-matching URLs pass through, plain/parenthesized/in-markdown cases per link type, `(this PR)` vs `(#N)` branch, range `sha..sha2` labels — table pinned across both replacers plus discussion variant.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", query: "avoidLinkLoss preventPrCommitLinkLoss", limit: 10 });
// → refined-github.source.github-helpers.prevent-link-loss.* Functions source/github-helpers/prevent-link-loss.ts
```

## Verdict
Adopt the replacer-trio + index-lookahead idempotence check + relative-reference suppression for any "paste URL → rich mention" feature on any host with markdown comments. Adapt the three grammars to your host's URL shapes, the label template to your house style, and swap `escapeRegex` for native `RegExp.escape` where available. Omit nothing else: dropping the paren check double-wraps user links.
