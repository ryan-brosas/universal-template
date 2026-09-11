<!-- capsule-v2 -->
# Click-to-edit links via handleClick interception — how do I make clicking a link inside an editor open my edit UI instead of navigating, without breaking caret placement?

**Source:** dub (AGPL-3.0; EE portions under apps/web/app/(ee)/LICENSE.md) `main@29df217a`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-dub`. **Question:** How is a plain click on a link mark converted into "open the edit modal at that link"?

## Provider editorProps.handleClick + openLinkModal
**Path/Symbol:** `packages/ui/src/rich-text-area/rich-text-provider.tsx:handleClick` (316–331) + `openLinkModal` (128–146); extension config at 196–202.
**Signature:** `handleClick(view: EditorView, pos: number, event: MouseEvent): boolean`; `openLinkModal(pos?: number): void`.
**Data Shape:** returns `true` to consume the click; modal state `{from,to,text,href}` captured from live selection after optional repositioning.

### Decisive source
```tsx
handleClick: (view, pos, event) => {
  if (editorProps?.handleClick?.(view, pos, event)) return true;   // consumer first
  if (view.editable && features.includes("links") &&
      event.target instanceof Element && event.target.closest("a[href]")) {
    openLinkModal(pos);
    return true;
  }
  return false;
},
// openLinkModal:
const chain = editor.chain();
if (pos !== undefined) chain.setTextSelection(pos);
chain.run();
if (editor.isActive("link")) editor.chain().extendMarkRange("link").run();
const { from, to } = editor.state.selection;
```

**Flow:** ProseMirror dispatches handleClick → consumer handler wins if it returned true → editable-only guard → DOM target must sit inside an `<a[href]>` → place caret at clicked pos → if the pos landed on a link mark, `extendMarkRange("link")` grows the selection to the WHOLE mark span → capture `{from,to}` of that span plus current href → open modal. Read-only editors fall through (no modal).
**Invariant:** `openOnClick: false` on the Link extension AND `Link.extend({inclusive: false})` are both required — default inclusive:true would keep typing after the cursor inside the link mark (every subsequent char auto-linked); `closest()` walks up because the click may land on a child node of the anchor.
**Probe:** `grep -n 'openOnClick' packages/ui/src/rich-text-area/rich-text-provider.tsx` → line 200; `grep -cF 'closest("a[href]")' packages/ui/src/rich-text-area/rich-text-provider.tsx` → **1**; `grep -n 'inclusive: false' packages/ui/src/rich-text-area/rich-text-provider.tsx` → line 197.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-dub", query: "RichTextProvider useRichTextContext", limit: 10 });
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-dub", query: "normalizeLinkHref RichTextLinkHoverTooltip", limit: 5 });
```

## Verdict
Adopt handleClick-consume + extendMarkRange capture for in-editor link editing; adapt the guard set to your feature model; omit nothing — read-only fall-through and consumer-priority ordering are load-bearing.
