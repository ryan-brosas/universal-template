<!-- capsule-v2 -->
# Image-link toolbar branch with window.prompt — how does the same Link button edit a text mark and an image node attribute through one entry point?

**Source:** dub (AGPL-3.0; EE portions under apps/web/app/(ee)/LICENSE.md) `main@29df217a`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-dub`. **Question:** When the selection is an image node, what changes about link editing (validation, removal, focus restoration)?

## LinkButton in RichTextToolbar
**Path/Symbol:** `packages/ui/src/rich-text-area/rich-text-toolbar.tsx:LinkButton` (142–214); state via `useEditorState` selector (146–157).
**Signature:** `LinkButton(): Button` — onClick branches on `editor.isActive("image")` + `imageControlsEnabled`.
**Data Shape:** active-state union `{isImageSelected, isLinkActive}` where `isLinkActive` also matches images carrying a href attr when imageControls is on; `canLink = !isImageSelected || imageControlsEnabled`.

### Decisive source
```tsx
if (isImageSelected && imageControlsEnabled) {
  const previousUrl = editor.getAttributes("image").href ?? "";
  const url = window.prompt("Link URL", previousUrl);
  const nodePos = editor.state.selection.from;      // capture BEFORE prompt steals focus
  if (url === null) return;                          // cancel
  if (!url.trim()) { editor.chain().focus().updateAttributes("image", { href: null }).setNodeSelection(nodePos).run(); return; }
  if (!isSafeLinkHref(url.trim())) { toast.error(…); editor.chain().focus().setNodeSelection(nodePos).run(); return; }
  editor.chain().focus().updateAttributes("image", { href: url.trim() }).setNodeSelection(nodePos).run();
  return;
}
openLinkModal();                                     // text selection → modal path
```

**Flow:** click → image selected? prompt() dialog seeded with current href → null=cancel; empty=unlink (`href: null`); unsafe=toast+refocus WITHOUT mutating; safe=update attr — every branch ends by re-selecting the node at the position captured before the prompt. Text-selection path delegates to the shared modal (selection-replay capsule).
**Invariant:** `nodePos` MUST be captured before `window.prompt()` — the prompt blocks and blurs the editor, invalidating the live selection afterwards; `setNodeSelection(nodePos)` after every chain restores the visual ring; note the asymmetry vs text links: no normalize ladder here, only strict verify (prompt returns raw user text; `https://dub.co` style input works because it parses).
**Probe:** `grep -n 'window.prompt' packages/ui/src/rich-text-area/rich-text-toolbar.tsx` → line 177; `grep -c 'setNodeSelection(nodePos)' packages/ui/src/rich-text-area/rich-text-toolbar.tsx` → **3**.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-dub", query: "RichTextToolbar LinkButton useEditorState", limit: 5 });
```

## Verdict
Adopt the one-button/two-target dispatch with pre-captured node position around blocking dialogs; adapt the prompt to your inline popover but keep cancel/empty/unsafe tri-state semantics; omit the imageControls coupling if you always allow image links.
