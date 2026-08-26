<!-- capsule-v2 -->
# DOM-event hover tooltip for ProseMirror-rendered anchors — how do I show a link preview over editor content that React does not own?

**Source:** dub (AGPL-3.0; EE portions under apps/web/app/(ee)/LICENSE.md) `main@29df217a`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-dub`. **Question:** How do you attach hover UI to elements ProseMirror renders outside the React tree, and when must it hide?

## RichTextLinkHoverTooltip
**Path/Symbol:** `packages/ui/src/rich-text-area/link-hover-tooltip.tsx:RichTextLinkHoverTooltip` (12–76).
**Signature:** `RichTextLinkHoverTooltip(): Portal | null` — state `{href: string; rect: DOMRect} | null`.
**Data Shape:** fixed-position portal to `document.body`, centered above the anchor rect (`-translate-x-1/2 -translate-y-full`), hidden whenever a modal is open.

### Decisive source
```tsx
const dom = editor.view.dom as HTMLElement;
const onMouseOver = (e) => {
  const anchor = e.target instanceof Element ? e.target.closest("a[href]") : null;
  if (anchor && dom.contains(anchor))
    setHovered({ href: anchor.getAttribute("href") ?? "", rect: anchor.getBoundingClientRect() });
};
const onMouseOut = (e) => {
  const anchor = /* closest("a[href]) */ …;
  const toAnchor = e.relatedTarget instanceof Element ? e.relatedTarget.closest("a[href]") : null;
  if (anchor && anchor !== toAnchor) setHovered(null);   // anchor→anchor moves keep it open
};
dom.addEventListener("mouseover", onMouseOver);
dom.addEventListener("mouseout", onMouseOut);
window.addEventListener("scroll", clear, true);          // capture phase
if (!hovered || linkModalState) return null;             // modal wins
```

**Flow:** mouseover anywhere in `editor.view.dom` resolves the nearest anchor → store href+rect → mouseout clears ONLY when leaving to a non-anchor target → any scroll (capture, all scrollables) clears → render is suppressed while `linkModalState` is set so the edit modal never fights its own tooltip.
**Invariant:** you CANNOT wrap ProseMirror-rendered anchors with React components — they are created by PM's view layer; delegation on `editor.view.dom` + `closest("a[href]")` + `dom.contains(anchor)` containment check is the pattern; scroll listener MUST use capture (`true`) because scroll events don't bubble.
**Probe:** `grep -c 'createPortal' packages/ui/src/rich-text-area/link-hover-tooltip.tsx` → **1** (import) +1 (call) = count via `grep -c createPortal` = **2 total lines**; `grep -c 'addEventListener' packages/ui/src/rich-text-area/link-hover-tooltip.tsx` → **3**.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-dub", query: "normalizeLinkHref RichTextLinkHoverTooltip", limit: 5 });
```

## Verdict
Adopt the delegated-DOM-events + capture-scroll-clear + modal-suppression triad for any hover UI over PM/CodeMirror content; adapt positioning tokens and max-width; omit the Tooltip component reuse in read-only markdown views (message-markdown.tsx wraps `<a>` directly there instead — different plane because React owns that DOM).
