<!-- capsule-v2 -->
# One provider, two serialization modes — how does the same editor feed markdown to a chat input and JSON to a form store?

**Source:** dub (AGPL-3.0; EE portions under apps/web/app/(ee)/LICENSE.md) `main@29df217a`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-dub`. **Question:** What exactly differs between the message-input wiring and the campaign-editor wiring of RichTextProvider?

## Consumer wiring pair
**Path/Symbol:** `apps/web/ui/shared/message-input.tsx:214-260` vs `apps/web/app/app.dub.co/(dashboard)/[slug]/(ee)/program/campaigns/[campaignId]/campaign-editor.tsx:688-741`.
**Signature:** chat: `features={["bold", "italic", "links"]} style="condensed" markdown` + `onChange={(editor) => setTypedMessage((editor as any).getMarkdown())}`; campaign: `features={[...DEFAULT_RICH_TEXT_FEATURES, "imageControls"]} style="relaxed"` + `onChange={(editor) => field.onChange(editor.getJSON())}` + `editable={!isLocked}` + signed-URL `uploadImage`.
**Data Shape:** chat persists markdown strings (`Markdown` extension registered only when `markdown` prop true — `contentType: "markdown"`); campaign persists ProseMirror JSON (round-trips variables/images losslessly).

### Decisive source
```tsx
// chat plane — apps/web/ui/shared/message-input.tsx:216-223
features={["bold", "italic", "links"]}   // no headings/variables/images → toolbar hides them
style="condensed" markdown autoFocus={autoFocus}
editorProps={{ handleDOMEvents: { keydown: (view, e) => {
  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) { e.preventDefault(); sendMessage(); return false; }
  if (e.key === ":") { /* emoji-picker trigger gated by block-start / whitespace / hardBreak */ }
}}}}
// campaign plane — campaign-editor.tsx:692-694
features={[...DEFAULT_RICH_TEXT_FEATURES, "imageControls"]} style="relaxed"
onChange={(editor) => field.onChange(editor.getJSON())}
```

**Flow:** provider registers Markdown extension + contentType per prop → consumers choose serialization at onChange time (getMarkdown vs getJSON) → feature subset drives BOTH extension registration and toolbar buttons from one array → cmd+Enter send and colon-emoji live in consumer-level handleDOMEvents, not the package.
**Invariant:** markdown mode is LOSSY for mention fallbacks in raw text but safe here because chat features exclude variables; JSON mode is required for anything carrying mention/image nodes; `style` only swaps PROSE_STYLES classes — never feature sets.
**Probe:** `grep -n 'condensed' apps/web/ui/shared/message-input.tsx` → line 217; `grep -n 'getMarkdown()' apps/web/ui/shared/message-input.tsx` → line 223; `grep -n 'getJSON()' 'apps/web/app/app.dub.co/(dashboard)/[slug]/(ee)/program/campaigns/[campaignId]/campaign-editor.tsx'` → line 694.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-dub", query: "getMarkdown getHTML EditorContent", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-dub", name_pattern: "PROSE_STYLES", limit: 5 });
```

## Verdict
Adopt the single-engine/multi-consumer pattern: features array + style preset + serialization chosen at onChange; adapt feature vocabularies per surface; omit EE campaign specifics (signed upload URL flow is recorded in the fraud/commission capsules' sibling plane).
