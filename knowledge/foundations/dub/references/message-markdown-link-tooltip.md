<!-- capsule-v2 -->
# Read-view link tooltip by component wrapping — how does the markdown READ plane show link previews differently from the editor plane?

**Source:** dub (AGPL-3.0; EE portions under apps/web/app/(ee)/LICENSE.md) `main@29df217a`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-dub`. **Question:** When React DOES own the DOM (rendered markdown), what replaces the delegated-DOM-event tooltip, and what prose spacing changed with it?

## MessageMarkdown anchor + prose contract
**Path/Symbol:** `apps/web/ui/messages/message-markdown.tsx:components.a` (84–92); prose classes 23–26; invert palette 39–55.
**Signature:** `a: ({node, ...props}) => <Tooltip content={<span …>{props.href}</span>}><a {...props} target="_blank" rel="noopener noreferrer" /></Tooltip>`.
**Data Shape:** react-markdown component override map; Tooltip shows the raw href (max-w-[200px], break-all) on hover of rendered links.

### Decisive source
```tsx
"prose-p:leading-5 prose-p:m-0 [&_p+p]:mt-2",   // was: prose-p:mb-4 prose-p:m-2.5
…
components={{
  a: ({ node, ...props }) => (
    <Tooltip content={<span className="… max-w-[200px] break-all …">{props.href}</span>}>
      <a {...props} target="_blank" rel="noopener noreferrer" />
    </Tooltip>
  ),
```

**Flow:** markdown renders → every `<a>` is wrapped at the COMPONENT level (React owns these nodes, unlike PM-rendered editor anchors) → hover reveals href → click opens new tab with noopener. Paragraph margins collapsed to `m-0` plus adjacent-sibling `p+p` spacing to match the chat compaction language.
**Invariant:** this is the DUAL of link-hover-tooltip.tsx: wrapping works here precisely because react-markdown output is plain React children — do not port one pattern into the other plane; `[&_p+p]:mt-2` only spaces ADJACENT paragraphs, leaving leading/trailing margins zero so bubbles stay tight.
**Probe:** `grep -n '\[&_p+p\]:mt-2' apps/web/ui/messages/message-markdown.tsx` → line 26; `grep -n 'noopener noreferrer' apps/web/ui/messages/message-markdown.tsx` → line ~91 inside components map.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-dub", query: "MessageMarkdown MessagesPanel", limit: 5 });
```

## Verdict
Adopt the component-wrap tooltip for read-only markdown and keep the delegated-events pattern for editors; adapt tooltip styling tokens; omit the invert-palette block if you have no dark chat surfaces.
