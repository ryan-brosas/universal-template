<!-- capsule-v2 -->
# Feature-gated TipTap provider assembly — how do I build one rich-text editor engine that serves a chat input and an email campaign composer without forking?

**Source:** dub (AGPL-3.0; EE portions under apps/web/app/(ee)/LICENSE.md) `main@29df217a`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-dub`. **Question:** How does the provider turn a static `features` array into the exact extension set, and which defaults must survive the port?

## RichTextProvider extension assembly
**Path/Symbol:** `packages/ui/src/rich-text-area/rich-text-provider.tsx:RichTextProvider` (97–377); gates at 180–302.
**Signature:** `RichTextProvider(props: PropsWithChildren<{ features?: RichTextFeature[]; markdown?: boolean; style?: keyof typeof PROSE_STYLES; uploadImage?; variables?; variableInfo?; editable?; autoFocus?; editorProps?; editorClassName?; onChange?; }>, ref: Ref<RichTextAreaProviderRef>)`.
**Data Shape:** `features` defaults to ALL of `["images","variables","links","headings","bold","italic","strike"]` (`DEFAULT_RICH_TEXT_FEATURES`, FEATURES const 34–42); optional add-on `"imageControls"`. Context value carries `{features, markdown, editable, variables, editor, isUploading, handleImageUpload, linkModalState, setLinkModalState, openLinkModal}` or `null`.

### Decisive source
```tsx
StarterKit.configure({
  heading: features.includes("headings") ? { levels: [1, 2] } : false,
  bold: features.includes("bold") ? undefined : false,
  italic: features.includes("italic") ? undefined : false,
  strike: features.includes("strike") ? undefined : false,
  link: false,                       // StarterKit's link is ALWAYS off
}),
...(features.includes("links") ? [Link.extend({ inclusive: false }).configure({ openOnClick: false })] : []),
...(markdown ? [Markdown] : []),     // contentType: markdown ? "markdown" : undefined
```

**Flow:** build extensions array from feature membership → `useEditor({editable: editable ?? true, autofocus: autoFocus ? "end" : false, ..., immediatelyRender: false})` → stash instance on `editorRef.current = editor` (line 339) so callbacks never capture stale closures → `useEffect` re-syncs `editor.setEditable(editable ?? true)` when prop changes → expose imperative `setContent` via `useImperativeHandle` → render children plus (when links enabled) `RichTextLinkModal` + `RichTextLinkHoverTooltip` inside the context provider.
**Invariant:** StarterKit's own Link extension must stay disabled (`link: false`) or the custom click-to-edit link flow double-registers; `immediatelyRender: false` is required under Next.js SSR (hydration mismatch otherwise); `editable ?? true` is passed explicitly so the Placeholder decoration renders even before the effect runs.
**Probe:** `grep -c 'features.includes(' packages/ui/src/rich-text-area/rich-text-provider.tsx` → **10** (each gate site); `grep -n 'link: false' packages/ui/src/rich-text-area/rich-text-provider.tsx` → line 191.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-dub", name_pattern: "PROSE_STYLES", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-dub", query: "RichTextProvider useRichTextContext", limit: 10, fields: ["signature", "name", "file"] });
```
(`openLinkModal`/`handleImageUpload` are method-local consts — invisible to BM25 and name_pattern; grep the provider file.)

## Verdict
Adopt the features-array → conditional-extension assembly, the always-off StarterKit link, `immediatelyRender: false`, and the ref-based stale-closure pattern; adapt `PROSE_STYLES` class strings to your Tailwind tokens (four presets: default/condensed/chat/relaxed); omit the specific feature names if your product needs a different vocabulary — the mechanism is the portable part. No upstream vitest suite covers this package (standing runner block: repo ships no node_modules); deterministic greps stand as evidence.
