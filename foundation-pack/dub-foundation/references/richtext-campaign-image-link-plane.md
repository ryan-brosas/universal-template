<!-- capsule-v2 -->
# Linked-image attribute with parse/render sanitization and cmd-click open — how do I let campaign images carry a hyperlink without ever rendering an unsafe href?

**Source:** dub (AGPL-3.0; EE portions under apps/web/app/(ee)/LICENSE.md) `main@29df217a`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-dub`. **Question:** How is the href stored on an image NODE (not a text mark), kept out of renderHTML, and opened safely on modifier-click?

## CampaignEditorImageExtension
**Path/Symbol:** `packages/ui/src/rich-text-area/campaign-editor-image.ts:CampaignEditorImageExtension` (13–130); factory `configureCampaignEditorImage` (132–138).
**Signature:** `configureCampaignEditorImage(options: Partial<ImageOptions> & {imageAltControls?: boolean}): Image extension` — `addNodeView()` returns `ReactNodeViewRenderer(ImageAltNodeView)` only when `imageAltControls` is set, else `null`.
**Data Shape:** custom node attr `{href: string | null}` (default null); render emits `data-linked-image=""` marker ONLY when safe; parse reads the closest `<a>` ancestor.

### Decisive source
```ts
href: {
  default: null,
  parseHTML: (element) => {
    const anchor = element.closest("a");
    const href = anchor?.getAttribute("href");
    return isSafeLinkHref(href) ? href : null;      // sanitize at EVERY boundary
  },
  renderHTML: () => ({}),                           // NEVER emit <a href> around <img>
},
addProseMirrorPlugins() { return [...(this.parent?.() ?? []), new Plugin({
  props: { handleDOMEvents: { mousedown: (view, event) => {
    if (!event.metaKey && !event.ctrlKey) return false;
    const img = event.target.closest("img[data-linked-image]");
    if (!img || !view.dom.contains(img)) return false;
    const pos = view.posAtDOM(img, 0);
    const href = view.state.doc.nodeAt(pos)?.attrs.href;
    if (isSafeLinkHref(href)) { event.preventDefault(); window.open(href, "_blank", "noopener,noreferrer"); return true; }
```

**Flow:** paste/import HTML with `<a><img></a>` → parseHTML hoists+verifies href onto the node → renderHTML deliberately drops it (no anchor in editor DOM; only a data marker) → user cmd/ctrl-clicks the marked image → plugin maps DOM→doc pos via `posAtDOM`, re-verifies, opens with noopener.
**Invariant:** `renderHTML(){return ({})}` is the security hinge — emitting the href would create a real link inside contenteditable (click-to-select becomes navigate); the attr survives round-trips because parseHTML accepts it back from serialized HTML; base64 sources are refused unless allowBase64 (`img[src]:not([src^="data:"])` rule at line 52).
**Probe:** `grep -c 'isSafeLinkHref' packages/ui/src/rich-text-area/campaign-editor-image.ts` → **5**; `grep -c 'data-linked-image' packages/ui/src/rich-text-area/campaign-editor-image.ts packages/ui/src/rich-text-area/image-alt-node-view.tsx` → **2 + 1 = 3 total lines across both files**; `grep -nF 'img[src]:not([src^="data:"])' packages/ui/src/rich-text-area/campaign-editor-image.ts` → line 52.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-dub", query: "configureCampaignEditorImage CampaignEditorImageExtension", limit: 5 });
```

## Verdict
Adopt the parse-sanitize/render-strip/modifier-click-recheck triple boundary for linked media nodes; adapt the modifier choice to platform conventions; omit the alt NodeView wiring if you don't ship imageControls (the same extension degrades to stock Image).
