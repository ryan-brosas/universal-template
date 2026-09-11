<!-- capsule-v2 -->
# Mintlify markup laundering — how do I emit generator HTML that a foreign MDX/Markdown parser renders correctly?

**Source:** modelcontextprotocol (specification) MIT `main@57ac4a2ec742e0cb7622d899b0f5d3bcf769fd69`; Codebase Memory `modelcontextprotocol`. **Question:** When my documentation generator emits HTML for a third-party MDX site, which transformations keep anchors, headings, collapsibles, and Markdown metacharacters rendering as intended inside the consumer's parser?

## Consumer-identity anchors + cheerio HTML laundering + entity-encoded metachars
**Path/Symbol:** `typedoc.plugin.mjs:renderReflection` (195–279), `SchemaPageRouter` (47–64), `MARKDOWN_SPECIAL_CHARS` block (6–13).
**Signature:** `function renderReflection(reflection: typedoc.DeclarationReflection, context: typedoc.DefaultThemeRenderContext): string`; `class SchemaPageRouter extends typedoc.StructureRouter { getFullUrl(target) { return "#" + this.getAnchor(target); } }`.
**Data Shape:** input = TypeDoc JSX-rendered HTML per reflection; output = `<div class="type">\n\n### \`FriendlyFullName\`\n\n…laundered HTML…\n</div>` block.

### Decisive source
```js
getAnchor(target) {
  // Must use `toLowerCase()` because Mintlify generates lower case IDs for Markdown headings.
  return super.getFullUrl(target).replace(".html", "").replaceAll(/[./#]/g, "-").toLowerCase();
}
// …inside renderReflection:
$(".tsd-tag-example").each((_, el) => {           // @example → collapsible <details>
  const namespacedId = `${context.getAnchor(reflection)}-${h4.attribs.id}`;
  $(h4).removeAttr("id"); $(h4).next().attr("id", namespacedId); // id INSIDE hidden content
  h4.tagName = "summary"; el.tagName = "details";
});
$("h1,h2,h3,h4,h5,h6").each((_, el) => {          // consumer owns the outline
  $(el).attr("data-typedoc-h", el.tagName[1]); el.tagName = "div";
});
content = content.replaceAll("\u00A0", "&nbsp;"). // NBSP as entity, not raw char
  replaceAll(/\n+</g, " <").                      // newlines around tags are not significant
  replaceAll(MARKDOWN_SPECIAL_CHARS_REGEX,        // [ _ * ` ~ \ $ { → hex entities
    char => MARKDOWN_SPECIAL_CHARS_HTML_ENTITIES[char]);
```

**Flow:** render in two shapes — interface/class ⇒ reflectionPreview code block + comment summary/tags + member blocks; type alias ⇒ memberDeclaration handles everything internally ⇒ cheerio pass: `@example` blocks become `<details><summary>` with ids reflection-namespaced (`${anchor}-${id}`) and moved INTO the hidden content so fragment navigation auto-expands; headings h1–h6 demote to `div[data-typedoc-h=N]` because Mintlify owns the page outline; `[id="see"],[id^="deprecated"]` lose their colliding ids and dangling permalink icons; `.tsd-member` folds signature text into its anchor span and drops the redundant signature + Optional chips ⇒ whitespace/entity laundering for "Mintlify's janky Markdown parser": NBSP pairs collapse to one, NBSP becomes `&nbsp;`, newlines before tags become spaces, and the eight Markdown specials `[ _ * \` ~ \ $ {` inside HTML are entity-encoded so the parser treats them as literal text.
**Invariant:** every generated anchor resolves under the CONSUMER's ID algorithm (lowercase, `[./#]→-`) — never under the generator's natural scheme; no generated markup may introduce heading levels, duplicate ids, or raw Markdown metacharacters into the host page.
**Probe:** `npm run check:schema:md` at HEAD ⇒ exit 0 pins the exact laundered bytes; grep the published `docs/specification/draft/schema.mdx` for `data-typedoc-h` / `<details>` / `&#x5B;`-style entities to see each transform live. No unit test exists — published artifacts + byte gate are the fixtures.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "modelcontextprotocol", query: "SchemaPageRouter getAnchor MARKDOWN_SPECIAL_CHARS", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt anchor-scheme mirroring of the downstream renderer, heading demotion when embedding generator output in a foreign outline, details/summary example collapsibles with hidden-content ids, and entity-encoding of Markdown metacharacters inside emitted HTML. Adapt the specific selectors (.tsd-*, tsd-tag-example) to your generator's DOM and your host's quirks list — the invariant is "derive identity the way the CONSUMER does," not these exact regexes. Omit cheerio/typedoc specifics if your stack renders directly to MDX components. Coverage: all cited symbols indexed no_recorded_issue/metadata_match (FULL graph, best-effort caveat); behavior pinned by the byte gate over published pages rather than a unit test.
