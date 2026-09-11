<!-- capsule-v2 -->
# Mention-node template variables with per-variable fallback — how do I represent merge-tag variables inside a rich-text document and render them losslessly in every mode?

**Source:** dub (AGPL-3.0; EE portions under apps/web/app/(ee)/LICENSE.md) `main@29df217a`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-dub`. **Question:** How does dub extend TipTap Mention so variables carry an optional fallback, serialize as `{{id | fallback}}` text, and offer a two-stage picker?

## RichTextProvider variable mention extension
**Path/Symbol:** `packages/ui/src/rich-text-area/rich-text-provider.tsx:259-301` (`Mention.extend`); picker at `packages/ui/src/rich-text-area/variables.tsx:suggestions` (42–111) + `Menu` (118–322).
**Signature:** `Mention.extend({ addAttributes(): {...this.parent?.(), fallback: {default: null; parseHTML; renderHTML}}; renderHTML({node}); renderText({node}) }).configure({ suggestion: suggestions(variables, variableInfo) })`.
**Data Shape:** node attrs `{id: string, fallback: string | null}`; HTML carries `data-type="mention" data-id=… data-fallback=…`; text form is `{{id}}` or `{{id | fallback}}` (space-pipe-space); `variableInfo?: Record<string, {description?, example?, hideExample?}>`.

### Decisive source
```tsx
renderHTML({ node }) {
  const label = node.attrs.fallback
    ? `{{${node.attrs.id} | ${node.attrs.fallback}}}`
    : `{{${node.attrs.id}}}`;
  return ["span", { class: "px-1 py-0.5 bg-blue-100 …", "data-type": "mention",
    "data-id": node.attrs.id,
    ...(node.attrs.fallback ? { "data-fallback": node.attrs.fallback } : {}) }, label];
},
renderText({ node }) {
  return node.attrs.fallback ? `{{${node.attrs.id} | ${node.attrs.fallback}}}` : `{{${node.attrs.id}}}`;
},
```

**Flow:** typing `@` opens the suggestion menu → `items` filters case-insensitively, ranks prefix matches first then alphabetical, caps 10 → Enter on `PartnerName` routes to a second-stage fallback input (`selectVar`: everything else commits `command({id, fallback: null})` immediately) → confirm commits the mention with the typed fallback → round-trip survives because both `renderHTML` (data-fallback) and `renderText` (`{{id | fallback}}`) encode it.
**Invariant:** the fallback attribute MUST be declared in `addAttributes` with parse+render hooks — without it `renderText`/`data-fallback` silently drop on paste/reload and email sends break; only `PartnerName` gets the fallback stage (hard-coded in `Menu.selectVar`, variables.tsx:144–151); menu items cap at 10 (`slice(0, 10)` twice).
**Probe:** `grep -c 'data-fallback' packages/ui/src/rich-text-area/rich-text-provider.tsx` → **3**; `grep -c 'PartnerName' packages/ui/src/rich-text-area/variables.tsx` → **1**; `grep -c 'slice(0, 10)' packages/ui/src/rich-text-area/variables.tsx` → **2**.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-dub", query: "suggestions updatePosition ReactRenderer", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the mention-as-template-variable pattern: custom attr + dual renderers + `renderText` serializer + two-stage picker keyed off a named variable; adapt the blue-chip styling, the `PartnerName` special-case name, and the 10-item cap to your product; omit the floating-ui positioning if your UI framework already has a popover primitive (but keep shift()+flip() semantics). Direct tests absent upstream for this package — runner-block standing.
