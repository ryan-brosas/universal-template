<!-- capsule-v2 -->
# CSS inliner fallback ladder — how do cross-origin stylesheets get captured when direct sheet access throws?

**Source:** openreplay AGPL-3.0 (tracker MIT) `main@99eb600`; Codebase Memory `openreplay`. **Question:** What is the try-order for capturing a `<link rel=stylesheet>`'s rules, and what browser quirks need patching?

## sheet → fetch → load-event retry; Safari colon + background-clip fixes
**Path/Symbol:** `tracker/tracker/src/main/app/observer/cssInliner.ts` — `inlineRemoteCss` (:3–98), fake-id base `1000000*99` (:1), `retryViaLoadEvent` (:59–86), `escapeImportStatement` (@import with quotes/layer/supports :235–253), `fixSafariColons` (:254–257), `fixBrowserCompatibilityIssuesInCSS` (:221–233), `absolutifyURLs` (:267+).
**Signature:** `inlineRemoteCss(node, id, baseHref, getNextID, insertRule, addOwner, forceFetch?, sendPlain?, onPlain?)`.
**Data Shape:** cssText pipeline: strip comments → parseCSS → per-rule stringify (import rules: prefer nested styleSheet stringify, else escaped @import statement, else raw cssText) → absolutify url() against sheet href.

### Decisive source
```ts
const sheet = node.sheet;
if (sheet && !forceFetch) {
  try { const cssText = stringifyStylesheet(sheet); if (cssText) { processCssText(cssText); return } } catch {}
}
// Fall back to fetching if we couldn't get or stringify the sheet
fetch(node.href).then(...).catch(() => retryViaLoadEvent())
```
```ts
function fixSafariColons(css) { // pseudo-class inside attribute selector
  return css.replace(/(\[[\w-]+[^\\])(:([\w-]+)\])/gm, '$1\\$2')
}
```

**Flow:** same-origin ⇒ read CSSOM directly; CORS-tainted ⇒ fetch text (may fail) ⇒ last resort wait for the link's load event then re-try sheet access; plain mode emits whole css via fake ids ≥ 99 000 000 to avoid colliding with node ids. Import statements are re-serialized preserving layer()/supports() and media lists.
**Invariant:** Every path must terminate in exactly one insertRule batch (id allocated only when !sendPlain). Never inline a stylesheet twice — the generation counter + setTimeout(0) in observer.ts guards session restarts.
**Probe:** `grep -c 'fakeIdHolder = 1000000 \* 99' tracker/tracker/src/main/app/observer/cssInliner.ts` → `1`; `grep -c 'retryViaLoadEvent()' tracker/tracker/src/main/app/observer/cssInliner.ts` → `3`; `grep -c 'webkit-background-clip: text;' tracker/tracker/src/main/app/observer/cssInliner.ts` → `2`; direct test `tests/cssInliner.test.ts` executed green.
**Coverage:** clean.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openreplay", query: "inlineRemoteCss stringifyStylesheet fixSafariColons escapeImportStatement", limit: 10 });
```

## Verdict
Adopt the three-tier ladder. Adapt quirks list per supported browsers. Omit plain-text mode unless your player renders style tags.
