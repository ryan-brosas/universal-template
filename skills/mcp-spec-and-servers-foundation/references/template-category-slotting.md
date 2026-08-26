<!-- capsule-v2 -->
# Template category slotting — how does a placeholder-driven generated reference stay complete and deterministically ordered as types evolve?

**Source:** modelcontextprotocol (specification) MIT `main@57ac4a2ec742e0cb7622d899b0f5d3bcf769fd69`; Codebase Memory `modelcontextprotocol`. **Question:** When a doc page is rendered by filling placeholder slots in a hand-authored template, how do I guarantee a newly added type can never silently vanish from the published docs — and that entries appear in a stable, protocol-meaningful order?

## Fail-closed @category slots + name-suffix ordering ladder
**Path/Symbol:** `typedoc.plugin.mjs:renderTemplate` (93–121), `renderCategory` (177–188), `getReflectionCategory` (158–161), `isRpcMethodCategory` (167–169), `getReflectionOrder` (137–152).
**Signature:** `function renderTemplate(template: string, pageEvents: typedoc.PageEvent[], theme): string`; `function renderCategory(category: string, events, theme): string`.
**Data Shape:** template slot lines `{/* @category <Name> */}`; each reflection's category = text of its `@category` JSDoc tag; RPC-method categories are those starting with a backtick + lowercase letter (`/^`[a-z]/`, e.g. `` `completion/complete` ``); output = concatenation of rendered reflections per slot.

### Decisive source
```js
const rendered = template.replaceAll(
  /^\{\/\* @category (.+) \*\/\}$/mg,
  (match, category) => { renderedCategories.add(category); return renderCategory(category, reflectionEvents, theme); }
);
const missingCategories = reflectionEvents.
  map((event) => getReflectionCategory(event.model)).
  filter((category) => category && !renderedCategories.has(category)).
  filter((category, i, array) => array.indexOf(category) === i).sort();
if (missingCategories.length > 0) {
  throw new Error("The following categories are missing from the schema page template:\n\n" +
    missingCategories.map((category) => `- ${category}\n`).join(""));
}
// ordering inside renderCategory, for backtick categories only:
order ||= +reflection2.name.endsWith("Request") - +reflection1.name.endsWith("Request");
// …RequestParams → ResultResponse → Result → Notification → NotificationParams…
order ||= reflection1.name.localeCompare(reflection2.name);
```

**Flow:** template regex replaces each slot with its category's reflections (a slot matching zero reflections throws `Invalid category`) ⇒ after substitution, every reflection category is diffed against the set of RENDERED slots; any leftover category aborts generation with the exact missing list. Within an RPC-method category, entries sort Request → RequestParams → ResultResponse → Result → Notification → NotificationParams via boolean-arithmetic comparators, falling back to `localeCompare` for non-RPC groups and ties.
**Invariant:** template slots and type categories must agree EXACTLY in both directions (fail-closed completeness — adding `@category foo` to schema.ts without adding a slot breaks the build loudly instead of dropping docs silently); display order is DATA derived from type-name suffixes, never a hand-maintained list.
**Probe:** `npm run check:schema:md` at HEAD ⇒ exit 0 (template covers all categories). RED twin (isolated /tmp copy): delete one `{/* @category … */}` line from a template copy ⇒ generation throws "The following categories are missing from the schema page template" listing it. The draft template's headings (`## JSON-RPC`, `` ## `completion/complete` ``, …) pin the slot grammar on disk.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "modelcontextprotocol", query: "getReflectionOrder getReflectionCategory isRpcMethodCategory", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt fail-closed placeholder templates (throw on unrendered content AND on empty slots) and convention-derived ordering (name-suffix ladder + deterministic tiebreak) for any generated reference surface. Adapt the slot syntax (@category comments vs your templater's directives) and the suffix vocabulary to your naming scheme. Omit MCP's specific wire-method suffix ladder unless your domain has the same request/params/result/notification shape family. Coverage: all five symbols indexed no_recorded_issue/metadata_match (FULL graph, best-effort caveat); behavior pinned by the repo gate + template fixture rather than a unit test.
