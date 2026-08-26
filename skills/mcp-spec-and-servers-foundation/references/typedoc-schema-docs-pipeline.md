<!-- capsule-v2 -->
# Typedoc schema docs pipeline — how do I publish a single-page API reference generated from TS protocol types and gate it byte-exactly in CI?

**Source:** modelcontextprotocol (specification) MIT `main@57ac4a2ec742e0cb7622d899b0f5d3bcf769fd69`; Codebase Memory `modelcontextprotocol`. **Question:** When my product publishes human-readable type documentation derived from the same TypeScript sources that generate my wire schema, how do I keep it deterministic enough for a regenerate-and-compare CI gate?

## Stdout single-page custom output + raw-byte cmp gate
**Path/Symbol:** `typedoc.plugin.mjs:load` (16–45) with `typedoc.config.mjs` (whole file) and `package.json` scripts `generate:schema:md` (:27) / `check:schema:md` (:37).
**Signature:** `export function load(app: typedoc.Application)` registering `app.outputs.addOutput("schema-page", async (outputDir, project) => …)` plus option `schemaPageTemplate`.
**Data Shape:** inputs `schema/<v>/schema.ts` (entry point) + `schema/<v>/schema.mdx` (template with `{/* @category X */}` slots); output = ENTIRE rendered page on process stdout; shell publishes via `> docs/specification/<v>/schema.mdx`, CI verifies via `| cmp <published> - || exit 1`.

### Decisive source
```js
app.outputs.addOutput("schema-page", async (outputDir, project) => {
  const template = await readFile(templatePath, { encoding: "utf-8" });
  app.renderer.router = new SchemaPageRouter(app);
  app.renderer.theme = new typedoc.DefaultTheme(app.renderer);
  const outputEvent = new typedoc.RendererEvent(outputDir, project, []);
  await app.renderer.theme.preRender(outputEvent);
  app.renderer.trigger(typedoc.RendererEvent.BEGIN, outputEvent);
  const pageEvents = buildPageEvents(project, app.renderer.router);
  process.stdout.write(renderTemplate(template, pageEvents, theme));
  // Wait for all output to be written before allowing the process to exit.
  await new Promise((resolve) => process.stdout.write("", () => resolve(undefined)));
})
```

**Flow:** `npm run generate:schema` runs json+md generators CONCURRENTLY (`&` … `wait`); per version typedoc loads `typedoc.config.mjs` (`sort: ["source-order"]` for declaration-order determinism; `excludeInternal`; `excludeTags` strips typescript-json-schema-only JSDoc like `@TJS-type`/`@nullable` so prose readers never see generator annotations), the plugin replaces site rendering with one stdout page, redirection writes the published file, and `check:schema:md` re-runs the IDENTICAL command piping into raw `cmp`. `.prettierignore` excludes `docs/specification/*/schema.{md,mdx}` so the formatter can never fight the byte gate.
**Invariant:** published bytes == plugin stdout bytes exactly; generation and verification share ONE code path differing only in where stdout is pointed; stdout is flush-awaited before exit so pipes never truncate.
**Probe:** `npm run check:schema:md` at HEAD ⇒ silent success exit 0 (byte equality over all six versions). RED twin (isolated /tmp copy, checkout untouched): perturb a generated copy ⇒ `cmp` reports first differing byte, `|| exit 1` fires.
**Compare-strictness taxonomy across the sibling gates:** schema.json = trim-compare inside the script; seps pages = Prettier-normalized compare (committed bytes ARE formatted); schema.mdx = RAW cmp (generator owns every byte AND `.prettierignore` fences the formatter out). Match compare strictness to who owns the bytes.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "modelcontextprotocol", query: "renderTemplate buildPageEvents", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the custom-tool-output→stdout→shell-pipe pattern (one deterministic render path serves both publish and verify) with a flush-await before exit, source-order sorting, and formatter exclusion for generated docs; adopt the compare-strictness-matches-byte-ownership rule when wiring multiple artifact gates. Adapt typedoc itself (any typed AST doc generator works — the contract is stdout + template slots, not typedoc). Omit Mintlify/npm-specific plumbing and the MCP version matrix. Coverage: both files indexed no_recorded_issue/metadata_match (FULL graph, best-effort caveat acknowledged); package.json is not graph-indexed (JSON not an indexed language) — cited from its recorded exact lines; no unit test exists for the plugin — the repo's own npm gate IS the probe.
