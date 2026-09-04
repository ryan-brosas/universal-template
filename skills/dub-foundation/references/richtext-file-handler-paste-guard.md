<!-- capsule-v2 -->
# Paste-vs-drop image ingestion guard — how do I accept pasted/dropped images without clobbering clipboard HTML or uploading junk MIME types?

**Source:** dub (AGPL-3.0; EE portions under apps/web/app/(ee)/LICENSE.md) `main@29df217a`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-dub`. **Question:** What are the exact FileHandler guards that separate a clean image paste from an HTML paste, and where does each upload get inserted?

## Provider FileHandler configuration
**Path/Symbol:** `packages/ui/src/rich-text-area/rich-text-provider.tsx:FileHandler.configure` (232–254); upload funnel `handleImageUpload` (148–175).
**Signature:** `onDrop(currentEditor, files: File[], pos: number)` / `onPaste(currentEditor, files: File[], htmlContent: string): boolean | void`.
**Data Shape:** allowed MIME set = `{image/png, image/jpeg, image/gif, image/webp}`; `handleImageUpload(file, editor, pos): Promise<void>` sets `isUploading` around an async insert; null upload result aborts silently (spinner clears, nothing inserted).

### Decisive source
```tsx
onPaste: (currentEditor, files, htmlContent) => {
  if (htmlContent) return false;      // let TipTap paste the rich HTML — never double-insert
  files.forEach((file) => handleImageUpload(file, currentEditor,
    currentEditor.state.selection.anchor));          // paste inserts at CARET
},
onDrop: (currentEditor, files, pos) => {
  files.forEach((file) => handleImageUpload(file, currentEditor, pos));  // drop uses DROP pos
},
```

**Flow:** drop → per-file upload at the exact drop position; paste with HTML payload → bail (`false`) so the editor processes markup normally; bare-image paste → upload at selection anchor → on success `insertContentAt(pos, {type:"image", attrs:{src}}).focus().run()` → `isUploading` gates the spinner overlay in RichTextArea and pointer-events in the toolbar.
**Invariant:** the `if (htmlContent) return false` guard is the whole point — returning without consuming lets the default paste pipeline run; dropping the guard makes every copy-paste from a web page ALSO fire an image upload of its bitmap; insertion position differs by channel (anchor vs pos) and must not be swapped.
**Probe:** `grep -nF 'if (htmlContent) return false;' packages/ui/src/rich-text-area/rich-text-provider.tsx` → line 245; `grep -c 'handleImageUpload(' packages/ui/src/rich-text-area/rich-text-provider.tsx` → **2** call sites (+ definition line).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-dub", query: "FileHandler allowedMimeTypes onPaste", limit: 5 });
```

## Verdict
Adopt the two-channel ingestion split and the htmlContent escape hatch; adapt the MIME allowlist to your storage constraints; omit inline/base64 handling unless you need offline drafts (upstream keeps allowBase64 off via parseHTML's `img[src]:not([src^="data:"])` rule in campaign-editor-image.ts).
