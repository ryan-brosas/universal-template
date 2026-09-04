<!-- capsule-v2 -->
# dom-formatters + parse-backticks — how do you linkify plain text (issues, URLs, `code`) inside rendered comments without double-processing or breaking copy-paste?

**Source:** refined-github MIT `main@3bbe6088fe301d0d5cf1ae751a49307005762a68`; Codebase Memory `refined-github`. **Question:** When injecting links into already-rendered rich text, what guards prevent re-linkifying your own output, shortening code-block URLs, and destroying backtick semantics?

## Linkify-and-shorten pipeline with self-exclusion class
**Path/Symbol:** `source/github-helpers/dom-formatters.tsx:linkifyIssues` / `linkifyUrls` / `shortenLink` / `parseBackticks` (:25–118); core splitter `source/github-helpers/parse-backticks.tsx:parseBackticks` (:10–26).
**Signature:** `linkifyIssues(currentRepo: {owner?: string; name?: string}, element: HTMLElement, options?): void`; `linkifyUrls(element: HTMLElement): void`; `shortenLink(link: HTMLAnchorElement): void`; `parseBackticksCore(description: string): DocumentFragment`.
**Data Shape:** All operate in-place on DOM elements. Shared marker class `rgh-linkified-code` (`linkifiedUrlClass`) marks generated `<a>`s so `shortenLink` can exclude them.

### Decisive source
```ts
// dom-formatters.tsx — linkifyUrls
if (element.textContent.length < 15) { // Must be long enough for a URL
	return;
}
if (elementExists(linkifiedUrlSelector, element)) {
	console.warn('Links already exist', element);
	throw new Error('Links already exist');
}
const linkified = linkifyUrlsToDom(element.textContent, {
	attributes: {rel: 'noreferrer noopener', class: linkifiedUrlClass},
});
// ...
zipTextNodes(element, linkified); // splices links into the ORIGINAL text nodes

// parse-backticks.tsx — index-parity split, not a global regex loop
const splittingRegex = /`` (?<double>.*?) ``|`(?<single>[^\n`]+)`/;
return string.split(splittingRegex).filter(part => part !== undefined);
// odd indices = code-span contents; even = plain text
```

**Flow:** length gate (≥15 chars) → idempotence gate (existing `.rgh-linkified-code` ⇒ THROW, because silent re-run would nest links) → build a parallel fragment of `<a>`s from `textContent` only → `zipTextNodes` splices them back so surrounding markup (emoji, mentions) survives. For issues: rewrite each produced link with GitHub's native hovercard data attributes (`data-hovercard-url`, `dataset.id = rgh-issue-<n>`) so the host's own title-fetch takes over. `shortenLink` runs AFTER and skips any link whose closest context isn't `.markdown-body` — protecting code blocks and code suggestions (#4759).
**Invariant:** The exclusion is CLASS-based, set at generation time; every producer must stamp `class: linkifiedUrlClass` or `shortenLink` will shorten its own links. Backtick parsing uses split-with-capture-groups where odd indices alternate with plain text — a `/g` regex replace cannot express this because `` `` `` (double-backtick, for literal backticks) must be tried before `` ` `` and empty spans dropped.
**Probe:** `source/github-helpers/dom-formatters.test.ts:28+` pins shorten-in-comment vs. avoid-shortening-in-code via snapshots; `source/github-helpers/parse-backticks.test.ts:11–104` pins the full grammar table: single/double backticks, backtick-in-code-span (`` `` ` ````), triple-backtick blocks left untouched (#3990), multiline rejection.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", query: "linkifyIssues linkifyUrls", limit: 10 });
// → refined-github.source.github-helpers.dom-formatters.linkifyIssues/.linkifyUrls Functions source/github-helpers/dom-formatters.tsx
```

## Verdict
Adopt the three-guard shape (length gate, throw-on-relinkify, class-based self-exclusion) plus zip-back splicing for ANY text-linkification feature on a rendered page, and the odd/even split parser for inline-code detection that must preserve copy-pasteable backticks (here via invisible `.sr-only` backtick spans around each `<code>`). Adapt the linkify libraries, the hovercard attribute names, and the `.markdown-body` scoping to the target host. Omit GitHub-specific issue-title fetch wiring if the host has no hovercard system.
