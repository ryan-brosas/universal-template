<!-- capsule-v2 -->
# Browser content extraction — CDP DOM → Readability → Turndown markdown

**Source:** dsh-template (no LICENSE, `pi-fovea-foundation@ffb36822ffbcbba509deebaf3ea9412a9ea8b2c4`); Codebase Memory `dsh-template`. **Question:** How does a CDP browser script extract a page's readable content as clean markdown, even under TrustedScriptURL restrictions, with a Readability parse and a fallback path?

## Readable content → markdown
**Path/Symbol:** `.dsh/skills/pack-frontend/browser-tools/browser-content.js` (whole file, 107 lines); `TIMEOUT` (11–15), the CDP DOM fetch (51–55), `htmlToMarkdown` (64–79), the Readability parse (59–61), the fallback (84–100).
**Signature:** `node browser-content.js <url>` → prints `URL:`/`Title:` + the extracted markdown; exits 1 on a 30s timeout or unreachable browser. Uses `puppeteer-core`, `@mozilla/readability` `Readability`, `jsdom` `JSDOM`, `turndown` + `turndown-plugin-gfm`.
**Data Shape:** `TIMEOUT = 30000` (global, `.unref()` so it does not hold the loop). Fetches `outerHTML` via CDP `DOM.getDocument({depth:-1,pierce:true})` + `DOM.getOuterHTML`, then `new JSDOM(outerHTML, { url: finalUrl })` → `new Readability(doc.window.document).parse()`.

### Decisive source
```js
// Global timeout — exit if the script takes too long.
setTimeout(() => { console.error("✗ Timeout after 30s"); process.exit(1); }, TIMEOUT).unref();

// Get HTML via CDP (works even with TrustedScriptURL restrictions).
const client = await p.createCDPSession();
const { root } = await client.send("DOM.getDocument", { depth: -1, pierce: true });
const { outerHTML } = await client.send("DOM.getOuterHTML", { nodeId: root.nodeId });
await client.detach();
const finalUrl = p.url();

const doc = new JSDOM(outerHTML, { url: finalUrl });
const reader = new Readability(doc.window.document);
const article = reader.parse();

function htmlToMarkdown(html) {
  const turndown = new TurndownService({ headingStyle: "atx", codeBlockStyle: "fenced" });
  turndown.use(gfm);
  turndown.addRule("removeEmptyLinks", {
    filter: (node) => node.nodeName === "A" && !node.textContent?.trim(),
    replacement: () => "",
  });
  return turndown.turndown(html)
    .replace(/\[\\?\[\s*\\?\]\]\([^)]*\)/g, "")
    .replace(/ +/g, " ").replace(/\s+,/g, ",").replace(/\s+\./g, ".")
    .replace(/\n{3,}/g, "\n\n").trim();
}

let content;
if (article && article.content) {
  content = htmlToMarkdown(article.content);
} else {
  // Fallback: strip script/style/nav/header/footer/aside, prefer main/article/[role=main]/.content/#content
  const fallbackBody = new JSDOM(outerHTML, { url: finalUrl }).window.document;
  fallbackBody.querySelectorAll("script, style, noscript, nav, header, footer, aside").forEach((el) => el.remove());
  const main = fallbackBody.querySelector("main, article, [role='main'], .content, #content") || fallbackBody.body;
  const fallbackHtml = main?.innerHTML || "";
  content = fallbackHtml.trim().length > 100 ? htmlToMarkdown(fallbackHtml) : "(Could not extract content)";
}
```

**Flow:** (1) set a 30s global timeout; (2) connect to :9222 under a 5s race; (3) `goto` with `waitUntil: "networkidle2"` raced against a 10s fallback; (4) fetch the full `outerHTML` via CDP (bypasses TrustedScriptURL); (5) `JSDOM` + `Readability.parse()`; (6) if an article parsed, convert its content to markdown (atx headings, fenced code, GFM, empty-link removal, whitespace normalization); (7) else fall back to stripping boilerplate and preferring a main/article/content element, with a `(Could not extract content)` sentinel if under 100 chars.

**Invariant:** CDP DOM fetch works even when `page.content()` is blocked by TrustedScriptURL; markdown is normalized (no empty links, no double spaces, no 3+ newlines); a too-short fallback yields the explicit sentinel, never empty output; the 30s timeout guarantees the script exits.

**Probe:** no direct test file exists. Verified by direct source read (file indexed `no_recorded_issue` + `metadata_match`). The CDP DOM fetch and Readability→Turndown pipeline are the executable contract.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dsh-template", query: "browser-content Readability Turndown CDP DOM", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the CDP DOM fetch (TrustedScriptURL-safe), the Readability→Turndown markdown pipeline, the empty-link rule, the whitespace normalization, and the boilerplate-stripping fallback. Adapt the selector list and the 100-char threshold to the host. Omit the 30s global timeout if the caller manages its own timeout.
