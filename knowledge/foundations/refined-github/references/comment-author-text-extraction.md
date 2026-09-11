<!-- capsule-v2 -->
# comment-author-and-text-extraction — how do you resolve "who wrote this" (including bots) from any element inside a comment, and how do you read rendered rich text BACK into plain markdown?

**Source:** refined-github MIT `main@3bbe6088fe301d0d5cf1ae751a49307005762a68`; Codebase Memory `refined-github`. **Question:** What identity-normalization rule handles `dependabot[bot]`/`app/name` variants across four comment layouts, and what is the inverse of the linkify pipeline?

## getCommentAuthor — closest-container + avatar-alt ladder
**Path/Symbol:** `source/github-helpers/get-comment-author.ts:getCommentAuthor` (:21–56).
**Signature:** `getCommentAuthor(anyElementInsideComment: Element): string`.
**Data Shape:** Returns login (`name[bot]` for bots, special-case `'Copilot[bot]'`). Works from ANY descendant element — resolves outward via `closest`.

### Decisive source
```ts
const avatar = closestElement([
	'.TimelineItem',                    // PR comments (+ pre-redesign issues)
	'.review-comment',                  // PR review comments
	'.react-issue-body', '.react-issue-comment',
	'[data-testid="comment-header"]',   // commit comments
], anyElementInsideComment)
	.querySelector(['.TimelineItem-avatar img', 'img.avatar',
		'img[data-testid="github-avatar"]', 'img[data-component="Avatar"]',
		'.octicon-copilot'])!;
if (avatar.matches('.octicon-copilot')) return 'Copilot[bot]';
const name = (avatar as HTMLImageElement).alt.replace(/^@/, '');
const appLink = closestElementOptional(['a[href^="/apps/"]',
	'a[href^="https://github.com/apps/"]'], avatar);
if (appLink && !name.endsWith('[bot]')) return name + '[bot]';
return name;
```

**Flow:** climb to the nearest comment container (4 layout generations supported in parallel) → find that container's avatar by its generation's selector → derive login from `alt` minus leading `@` → if an `/apps/` link wraps the author and alt didn't already carry `[bot]`, append it.
**Invariant:** Bot identity comes from TWO independent signals (alt suffix OR apps-link ancestry) and both must be checked — either alone misses one of GitHub's renderings; the `[bot]` suffix must never be doubled.
**Probe:** No direct unit test (host-DOM bound); docstring pins the three bot URL forms (`name[bot]`, `app/name`, `apps/name`) with live example links. Caveat recorded.

## parseRenderedText — rendered DOM → markdown-ish source
**Path/Symbol:** `source/github-helpers/parse-rendered-text.ts:parseRenderedText` (:5–23) + opt-out marker `excludeFromDomTextExtraction` (:3).
**Signature:** `parseRenderedText(element: Element): string`.
### Decisive source
```ts
return getTextNodes(element).map(node => {
	if (node.parentElement?.tagName === 'CODE') return `\`${node.nodeValue?.trim()}\``;
	if (node.parentElement?.tagName === 'BUTTON'
		|| node.parentElement?.classList.contains(excludeFromDomTextExtraction)) return '';
	return node.nodeValue;
}).join('').trim();
```
**Flow:** TreeWalker over text nodes → `<code>`-wrapped nodes re-backtick (inverse of parseBackticks) → BUTTON descendants and `.rgh-exclude-from-dom-text-extraction` marked nodes drop out → concatenate + trim.
**Invariant:** This is the EXACT inverse contract of `text-linkify-pipeline.md`: features that add UI inside comment bodies MUST mark their insertions with `excludeFromDomTextExtraction` or reading back the comment picks up feature chrome as user text. Buttons are dropped unconditionally because GitHub renders action labels inline.
**Probe:** No direct unit test; round-trip behavior pinned indirectly by parse-backticks tests + consumer features. Caveat recorded.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", query: "getCommentAuthor parseRenderedText", limit: 10 });
// → refined-github.source.github-helpers.get-comment-author.getCommentAuthor / parse-rendered-text.parseRenderedText
```

## Verdict
Adopt the dual-signal bot normalization for any host with app accounts, and the mark-then-extract round-trip discipline whenever extensions both INJECT UI into and READ text from the same region. Adapt container/avatar selector ladders per host layout generation; keep the extraction marker convention — it's the piece porters always forget.
