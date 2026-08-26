<!-- capsule-v2 -->
# Selection-replay link save vs insert — how do I edit a link mark in place when text is unchanged but replace it atomically when the user rewrote the label?

**Source:** dub (AGPL-3.0; EE portions under apps/web/app/(ee)/LICENSE.md) `main@29df217a`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-dub`. **Question:** Why does the link modal replay the captured `{from, to}` selection before mutating, and what decides setLink vs insertContent?

## RichTextLinkModalInner.handleSave
**Path/Symbol:** `packages/ui/src/rich-text-area/link-modal.tsx:RichTextLinkModalInner` (34–169; save at 48–82, delete at 84–95).
**Signature:** `handleSave(e: FormEvent): void` over state `{from: number; to: number; text: string; href: string}` (`RichTextLinkModalState`).
**Data Shape:** modal opens with frozen `{from, to, text: doc.textBetween(from,to," "), href: getAttributes("link").href ?? ""}`; `isEditing = Boolean(state.href)`.

### Decisive source
```tsx
const trimmedText = text.trim();
const chain = editor.chain().focus().setTextSelection({ from: state.from, to: state.to });
if (trimmedText && trimmedText === state.text.trim()) {
  chain.setLink({ href: finalHref });            // label unchanged → mark-only edit
} else {
  chain.insertContent([{ type: "text", text: trimmedText || finalHref,
    marks: [{ type: "link", attrs: { href: finalHref } }] }]);  // new label → replace node
}
chain.run();
```

**Flow:** open captures selection+text+href → user edits either field → Save re-selects the ORIGINAL range (the editor moved focus/caret since capture) → unchanged-label path applies the mark to existing text; changed-label (or empty-label→href-as-text) path inserts fresh linked text replacing the range → `setLinkModalState(null)` closes. Delete replays the same selection then `unsetLink()`.
**Invariant:** EVERY mutation must replay `{state.from, state.to}` first — without it the mark lands wherever the caret drifted while the modal was open (the editor keeps live focus); empty label falls back to the URL itself as display text (`trimmedText || finalHref`); close refocuses the editor via `setTimeout(() => editor?.commands.focus(), 0)`.
**Probe:** `grep -cF 'setTextSelection({ from: state.from, to: state.to })' packages/ui/src/rich-text-area/link-modal.tsx` → **2** (save + delete); `grep -nF 'trimmedText === state.text.trim()' packages/ui/src/rich-text-area/link-modal.tsx` → line 67.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-dub", query: "RichTextLinkModalInner handleSave setLink", limit: 5 });
```

## Verdict
Adopt the frozen-state + selection-replay pattern for any deferred editor dialog (works for comment-edit modals too); adapt the two-path split if your editor API differs but keep "replay range before mutate"; omit the mobile autoFocus toggle if you have no responsive constraint.
