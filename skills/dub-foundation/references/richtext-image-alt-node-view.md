<!-- capsule-v2 -->
# Image node view with alt-text popover — how do I overlay editable controls on an image node without ProseMirror swallowing the interactions?

**Source:** dub (AGPL-3.0; EE portions under apps/web/app/(ee)/LICENSE.md) `main@29df217a`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-dub`. **Question:** How does the Alt button survive inside a contenteditable document, and when does it persist?

## ImageAltNodeView
**Path/Symbol:** `packages/ui/src/rich-text-area/image-alt-node-view.tsx:ImageAltNodeView` (11–136).
**Signature:** `ImageAltNodeView({node, editor, updateAttributes, extension, selected}: ReactNodeViewProps)`.
**Data Shape:** renders `<img>` + absolutely-positioned Popover button; attrs `{src, alt: string | null, title?, href?}`; save writes `alt: trimmed || null`.

### Decisive source
```tsx
const stopEvent = (event) => { event.preventDefault(); event.stopPropagation(); };
<div className="absolute bottom-2 right-2 …" contentEditable={false}>
  <Popover onOpenAutoFocus={(e) => { e.preventDefault(); inputRef.current?.focus(); }} …>
    <Input onBlur={() => saveAlt(altText)}
      onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); saveAlt(altText); setOpen(false); } }} />
```

**Flow:** hover reveals the Alt chip (opacity-0 group-hover unless alt exists or popover open — persistent indicator once set) → open forces focus into the input via `onOpenAutoFocus` preventDefault → blur OR Enter persists through `updateAttributes({alt: trimmed || null})` → Escape closes without saving; `useEffect` closes the popover whenever `editor.isEditable` flips false; local state re-syncs from `node.attrs.alt`.
**Invariant:** every interactive child of a NodeView MUST be wrapped in `contentEditable={false}` (else PM treats keystrokes as doc edits and the button can't be clicked reliably); `onMouseDown={stopEvent}` prevents PM from hijacking mousedown for selection/drag; empty-after-trim saves as `null` so `hasAlt` stays honest; the `<img>` carries `data-drag-handle` for node dragging.
**Probe:** `grep -c 'updateAttributes' packages/ui/src/rich-text-area/image-alt-node-view.tsx` → **3**; `grep -n 'contentEditable={false}' packages/ui/src/rich-text-area/image-alt-node-view.tsx` → line 84; `grep -c 'saveAlt(altText)' packages/ui/src/rich-text-area/image-alt-node-view.tsx` → **2**.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-dub", query: "ImageAltNodeView saveAlt", limit: 5 });
```

## Verdict
Adopt the contentEditable={false} island pattern + focus-steal prevention + trim-to-null persistence for any NodeView chrome; adapt the accessibility copy and delivery-rate rationale to your product; omit the drag-handle attribute if your editor disables node dragging.
