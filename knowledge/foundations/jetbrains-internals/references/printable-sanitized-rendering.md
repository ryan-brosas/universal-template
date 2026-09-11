<!-- capsule-v2 -->
# Printable sanitized rendering - how does a host-rendered console display user-influenced text, styles, and links without XSS?

**Source:** PhpStorm Light installed build PS-262.9421 (proprietary; cite-only); Codebase Memory `jetbrains-phpstorm-light`. **Question:** How do you render host-supplied evaluation output (which embeds user program data) in a privileged embedded browser safely?

## webConsole utils.js rendering
**Path/Symbol:** `plugins/javascript-debugger/webConsole/utils.js:createTextNode` (:103-126), `addUserStyles` (:70-86) + `userCssPrefixesWhiteList` (:65-68), `addHighlightHandler` (:88-97), `isLinkType` (:11-13); consumers `WebConsole.print/_prepareNode` (`WebConsole.js:386-431`).
**Signature:** `createTextNode(printable) → Element`; `addUserStyles(jsToken, node)`; printable = `{type, text: string[], inlineStyles: string[], styleClasses, iconURL?, deferred?, id, deferredID?}`.
**Data Shape:** `text[i]` entries are JSON STRING LITERALS (quotes and escapes included); one span per entry; `inlineStyles[i]` parallel array from the host.

### Decisive source
```js
// text arrives as a JSON literal — decode, never innerHTML:
span.appendChild(document.createTextNode(JSON.parse('"' + printable.text[0] + '"')));

function addUserStyles(jsToken, node) {
  const buffer = createElement('span');            // DETACHED scrub span
  buffer.setAttribute('style', jsToken.userStyle); // let the CSSOM parse it
  for (let i = 0; i < buffer.style.length; i++) {
    const property = buffer.style[i];
    if (userCssPrefixesWhiteList.some(p => property.startsWith(p)))   // background/border/color/font/line/margin/padding/text + -webkit-* twins
      userStyles[property] = buffer.style[property];
  }
  for (const key in userStyles) node.style[key] = userStyles[key];    // copy property-by-property
}
```
Link wiring (`WebConsole.js:407-415`): any type ending `-link` gets `onclick`/`navigateAction → callJVM("navigate", [printable.id])` and is registered as a navigatable; MESSAGE_LINK printables insert `beforebegin` (inline within the message flow) instead of appendChild. Deferred printables park their placeholder in `deferredMap.set(printable.id, newNode)` and `resolveDeferred` swaps by `deferredID`. DOM-typed tokens get hover handlers `callJVM('highlight'/'hideHighlight', [id])`.

**Flow:** All text goes through createTextNode after JSON-literal decode — escapes/newlines decode correctly while script injection is structurally impossible. Console-style custom CSS (`console.log("%c...", style)`) is parsed by a detached span's CSSOM, then only whitelist-prefix properties are copied onto the real node — `position:fixed`, `url()` exfiltration tricks, etc. never reach the live tree. Navigation never passes raw URLs across the bridge — only the printable's opaque id.
**Invariant:** no HTML string ever becomes markup; user styles pass through CSSOM parsing + prefix whitelist; cross-boundary actions reference ids, not payloads.
**Probe:** DOM-bound → byte-exact content pins executed: JSON.parse decode → utils.js:116; `'-webkit-background'` whitelist head → :66; `offsetParent === null` isHidden → :169. Whole-file read confirms detached-buffer copy loop :70-86.
**Coverage caveat:** coverage no_recorded_issue @ gen 2026-08-24T13:57:05Z.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-phpstorm-light", query: "user style whitelist highlight printable", file_pattern: "*webConsole*", limit: 5 });
```

## Verdict
Adopt JSON-literal→createTextNode plus CSSOM-scrub-and-whitelist for ANY console that renders program output or `%c`-style user styles inside a privileged webview. Adapt the whitelist prefixes to your design system. Omit deferred-printable parking unless your host streams values asynchronously.
