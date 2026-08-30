<!-- capsule-v2 -->
# commit-message-trailer-normalization — what must survive when a PR becomes one squash commit?

**Source:** refined-github MIT `main@3187161079033cc1eda1731044ba8a2fdd7b69b4`; Codebase Memory `refined-github`. **Question:** Squash-merge rewrites a PR into a single commit whose message GitHub pre-fills with co-authors, signoffs, and closing keywords. How do you clean that message (or parse/strip its conventional prefix) WITHOUT destroying the trailers that carry legal/credit semantics?

## Set-based trailer preservation with canonical casing
**Path/Symbol:** `source/helpers/clean-commit-message.ts` — `cleanCommitMessage` :5–42 (+ `parseUserFromEmail` :1–3).
**Signature:** `cleanCommitMessage(message: string, closingKeywords = false, excludeUsers: string[] = []): string`.
**Data Shape:** input is the raw squash-description text; output is `\n`-joined preserved lines (empty string when nothing survives).

### Decisive source
```ts
	for (const match of message.matchAll(/co-authored-by: (?<author>[^\n]+)/gi)) {
		const {author} = match.groups!;
		const username = parseUserFromEmail(author);
		if (username && excludeUsers.includes(username)) {
			continue;
		}
		preservedContent.add('Co-authored-by: ' + author);
	}
	// …same shape for signed-off-by → 'Signed-off-by: '
	if (!closingKeywords) {
		return [...preservedContent].join('\n');
	}
	for (const [line] of message.matchAll(/(?:fix|fixe|close|resolve)(?:s|d)?\s+(?:#\d+|https?:\S+)/gi)) {
		preservedContent.add(line);
	}
```
```ts
function parseUserFromEmail(author: string): string | undefined {
	return /<(?:\d+\+)?(?<username>[^<>@]+)@users\.noreply\.github\.com>/i.exec(author)?.groups?.username;
}
```

**Flow:** scan `co-authored-by:` lines case-insensitively → for each, extract the GITHUB PRIVACY EMAIL username (`<id+user@users.noreply.github.com>`, numeric prefix OPTIONAL to cover legacy pre-July-2017 emails) → drop the line only if that username is in excludeUsers → re-emit in CANONICAL casing into a Set (casing variants dedupe) → same pass for `signed-off-by:` (DCO) → if closingKeywords, additionally preserve `fix/fixe/close/resolve(s|d)? #num-or-URL` lines.
**Invariant:** (1) dedup happens via canonical-cased Set membership, so 'Co-authored-by' vs 'co-authored-by' of the same author collapses to one line; (2) exclusion keys on the PRIVACY EMAIL username, never on display name — a non-privacy email is kept even when the name matches an excluded user (test-pinned); (3) the optional `(\d+\+)?` prefix in the email regex is load-bearing for legacy emails (test-pinned: `someuser@users.noreply.github.com` without prefix IS dropped); (4) closing-keyword retention is OFF by default and exists ONLY because GitHub does not auto-close issues when merging into a non-default branch (#4531).
**Probe:** `source/helpers/clean-commit-message.test.ts` — 15 assertions: empty/clean inputs → empty; multi-co-author preservation; casing dedupe; signed-off-by dedupe; both trailers together; dependabot[bot] privacy-email exclusion (drop-only-matching, keep-others, keep-on-non-match, keep-on-non-privacy-email, legacy-prefix-less drop); closing keywords dropped by default / kept with flag / multiple kept. Read in full this pass; NOT executed (standing runner block).

## Consumer: clear the squash description, keep an Undo
**Path/Symbol:** `source/features/clear-pr-merge-commit-message.tsx` — `clear` :18–60, registration :66–78.
**Signature:** feature init via `observe('textarea[placeholder="Add an optional extended description…"]', clear, {signal})`.

### Decisive source
```ts
	if (!/squash/i.test($(confirmMergeButton).textContent)) {
		return;
	}
	const originalMessage = messageField.value;
	const author = getConversationAuthor();
	let cleanedMessage = cleanCommitMessage(originalMessage, !await isPrAgainstDefaultBranch(), [author]);
	if (cleanedMessage === originalMessage.trim()) {
		return;
	}
	cleanedMessage = cleanedMessage ? cleanedMessage + '\n' : '';
	// Do not use `text-field-edit` #6348
	setReactTextareaValue(messageField, cleanedMessage);
```

**Flow:** gate on the merge button actually saying "squash" → compute closingKeywords = PR targets NON-default branch → excludeUsers = [PR author] (GitHub auto-adds the author as co-author on squash, so it must be stripped) → no-op if nothing changed → write through `setReactTextareaValue` (native setter + input event; the comment bans the older text-field-edit helper, #6348) → attach an Undo/Redo note button that toggles between original and cleaned values.
**Invariant:** (1) 1-commit PRs are EXCLUDED at registration (`countElements('.TimelineItem.js-commit') === 1`, #3140) — there is no merge rewrite to clean; (2) the no-op check compares against `originalMessage.trim()` (not raw) so whitespace-only differences don't trigger a write; (3) the trailing `'\n'` is appended only when content survives, keeping the field either empty or well-formed.
**Probe:** no direct unit test (browser-bound). Executed pins: `grep -n "squash" source/features/clear-pr-merge-commit-message.tsx` → line 19; `grep -n "text-field-edit" source/features/clear-pr-merge-commit-message.tsx` → line 32. Live `trace_path inbound cleanCommitMessage` → callers_total 1 (this feature's `clear`).

## Closed-type conventional-commit parsing
**Path/Symbol:** `source/helpers/conventional-commits.ts` — `conventionalCommitRegex` :2, type map :6–17, `parseConventionalCommit` :20–43.
**Signature:** `parseConventionalCommit(commitTitle: string): undefined | {rawType: string; type: string; scope?: string; raw: string}`.

### Decisive source
```ts
export const conventionalCommitRegex = /^(?<type>\w+)(?:\((?<scope>.+?)\))?(?<major>!)?: */;
// Do not send PRs for types not listed here: …
// No more types will be added nor do we accept options.
const types = new Map([['feat', 'Feature'], ['fix', 'Fix'], ['chore', 'Chore'], ['revert', 'Revert'], ['style', 'Style'], ['docs', 'Docs'], ['build', 'Build'], ['refactor', 'Refactor'], ['test', 'Test'], ['ci', 'CI'], ['perf', 'Performance']]);
```
```ts
	const match = conventionalCommitRegex.exec(commitTitle);
	if (!match?.groups?.type) { return; }
	const {type: rawType, scope, major} = match.groups;
	const type = types.get(rawType.toLowerCase());
	if (!type) { return; }
	return {rawType, type: major ? `${type}!` : type, scope: scope ? `${scope}: ` : undefined, raw: match[0]};
```

**Flow:** anchored regex captures type / optional scope / optional breaking `!` / colon + trailing spaces as `raw` → type lookup is LOWERCASED (capitalized titles like 'Feat:' work) → unknown type returns undefined (the map is deliberately CLOSED — comment: "No more types will be added nor do we accept options") → `!` decorates the display type ('Fix!') → scope comes back PRE-FORMATTED as `'scope: '` (trailing colon+space) or undefined.
**Invariant:** (1) returning undefined (not a partial object) for unknown types lets consumers early-return silently; (2) `raw` is the exact matched prefix — the consumer removes exactly this from the title text node; (3) empty parens `feat():` yield undefined because the non-greedy scope group can't match empty; (4) the scope's pre-formatted trailing ': ' is a contract with the consumer's rendering, not an accident.
**Probe:** `source/helpers/conventional-commits.test.ts` — 28 inline-snapshot cases across lowercase AND uppercase suites: plain/scope/breaking combinations, 'revert(scope)' nesting, space-in-scope, paren-in-title, bare 'fix:' (raw has no trailing space), unknown type / plain title / empty parens / broken spacing all → undefined. Read in full this pass; NOT executed (runner block).

## Consumer: label commit titles, strip the prefix from the text node
**Path/Symbol:** `source/features/conventional-commits.tsx` — `renderLabelInCommitTitle` :19–48, `init` :50–52.
**Signature:** observes `${is(commitTitleInLists)} > span > a:first-child`.

### Decisive source
```ts
	if (
		// Skip commits that are _only_ "ci:" without anything else. Rare but it would be confusing to show just the label
		commit.raw === textNode.textContent
		&& !commitTitleElement.nextElementSibling
		// Ensure that the element contains only plain text, not stuff like <code>
		&& commitTitleElement.childElementCount < 1
	) {
		return;
	}
	commitTitleElement.prepend(
		<span className="IssueLabel hx_IssueLabel mr-2 tmp-mr-2" rgh-conventional-commits={commit.rawType.toLowerCase()}>
			{commit.type}
		</span>,
		// Keep scope outside because that's how they're rendered in release notes as well
		commit.scope ? <span className="color-fg-muted">{commit.scope}</span> : '',
	);
	removeTextInTextNode(textNode, conventionalCommitRegex);
```

**Flow:** parse the title's first text node → skip if the ENTIRE visible title is just the prefix with no sibling element (a bare "ci:" would render as a confusing lone label) → skip if the element contains child elements (only plain-text titles are rewritten) → prepend IssueLabel span (attribute carries lowercased rawType for CSS targeting) + muted scope span → remove exactly the regex-matched prefix from the text node.
**Invariant:** the two skip guards are ordered before any mutation; the scope renders OUTSIDE the label deliberately (release-note parity); removal uses the shared `conventionalCommitRegex` so parse and strip can never disagree about the prefix boundary.
**Probe:** no direct unit test (DOM-bound). Executed pins: `grep -n "childElementCount" source/features/conventional-commits.tsx` → line 33; `grep -n "removeTextInTextNode" source/features/conventional-commits.tsx` → lines 16, 47. Live `trace_path inbound parseConventionalCommit` → callers_total 1 (this feature).

## Trailing-#N strip and its inverse machine
**Path/Symbol:** `source/helpers/pr-commit-cleaner.ts` — `cleanPrCommitTitle` :5–7 (whole file 7 lines); consumer `source/features/sync-pr-commit-title.tsx` — `formatPrCommitTitle` :22–24, `updatePrTitle` :64–73.
**Signature:** `cleanPrCommitTitle(commitTitle: string, pr: number): string`.

### Decisive source
```ts
export default function cleanPrCommitTitle(commitTitle: string, pr: number): string {
	return commitTitle.replace(new RegExp(String.raw`\(#${pr}\)\s*$`), '').trim();
}
```
```ts
export function formatPrCommitTitle(title: string, prNumber = getConversationNumber()!): string {
	return `${title} (#${prNumber})`;
}
// …on merge submit:
const title = cleanPrCommitTitle(getCurrentCommitTitle(), getConversationNumber()!);
await api.v3(`pulls/${getConversationNumber()!}`, {method: 'PATCH', body: {title}});
```

**Flow:** the strip removes ONLY a TRAILING `(#N)` matching the CURRENT PR number (anchored `\s*$`) plus surrounding trim → the consumer is the inverse machine: it APPENDS ` (#N)` to the PR title to fill the squash commit field (observe on field appearance + on PR-title change), and on submit PATCHes the PR title back to the cleaned value via api.v3.
**Invariant:** (1) '(fixes #123)' and wrong-number '(#23454)' are NOT stripped (test-pinned) — the anchor + exact-number match prevent eating closing keywords; (2) format/strip are exact inverses only for the append shape ` (#N)` — the feature owns both sides, so the contract is internal; (3) the Cancel button unloads the whole feature (`features.unload(import.meta.url)`) rather than reverting state.
**Probe:** `source/helpers/pr-commit-cleaner.test.ts` — 5 assertions: exact strip, padded strip, no-op without suffix, '(fixes #123)' untouched, wrong number untouched. Read in full this pass; NOT executed (runner block). Executed pin: `grep -n "String.raw" source/helpers/pr-commit-cleaner.ts` → line 6. Live `trace_path inbound cleanPrCommitTitle` → callers_total 1 (sync-pr-commit-title updatePrTitle).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", query: "cleanCommitMessage parseConventionalCommit cleanPrCommitTitle", mode: "ids" });
// total: 3, line-exact: clean-commit-message.ts 5-42 · conventional-commits.ts 20-43 · pr-commit-cleaner.ts 5-7
await mcp.codebase_memory.trace_path({ project: "refined-github", function_name: "cleanCommitMessage", direction: "inbound" });
// callers_total: 1 each for all three helpers — one dedicated consumer feature per helper
```
Executed 2026-08-28 @ pin 3187161 via vendor CLI (identical tool surface).

## Verdict
Adopt the Set-based canonical-casing trailer preservation, the privacy-email-keyed exclusion (with the optional numeric prefix), the conditional closing-keyword retention, the CLOSED type map with lowercased lookup and pre-formatted scope, and the anchored trailing-#N strip — all are host-agnostic string mechanics with direct-test-pinned boundaries. Adapt the trailer names if your host uses different conventions, the squash-button detection, and the textarea-write helper to your host's controlled-input contract. Omit the RGH-specific Undo note copy and wiki links. Coverage caveat: `no_recorded_issue` @ gen 2026-08-24T14:04:43Z on all 9 cited paths; all three direct tests read in full (48 assertions total) but NOT executed (standing runner block); consumer features are browser-bound (no upstream tests). Cross-reference: react-controlled-input-writers.md (setReactTextareaValue), api-rest-wrapper.md (api.v3 PATCH), route-context-url-algebra.md (getConversationNumber).
