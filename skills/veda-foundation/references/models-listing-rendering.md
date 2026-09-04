<!-- capsule-v2 -->
# Models listing rendering — how do you render one structured discovery result as both human text and clean JSON, with honesty furniture that never pollutes the machine path?

**Source:** Veda (`veda-ts`, MIT, `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6`); Codebase Memory `veda`. **Question:** A "what models can I use" command produces a rich structured result (per-backend catalogs, provenance tags, warnings, caps). How do you serve it to a human AND a machine from ONE document, so warnings never leak onto stdout as prose in JSON mode, and the text view tells the user exactly how to see what was capped?

## Connected graph-selected seam
**Path/Symbol:** `src/commands/models.ts` whole file (88L): `SOURCE_LABEL` (:19–24), `modelLine` (:26–32), `formatBackend` (:34–67), `formatModelsText` (:69–75), `handleModels` (:77–88). Consumes `ModelsResult`/`BackendModelCatalog`/`CatalogModel` from `src/agent/model-catalog.ts` (see `model-catalog-discovery.md`).
**Signature:** `formatModelsText(result: ModelsResult): string`; `handleModels(config: ModelsConfig): Promise<void>`; `modelLine(m: CatalogModel): string`.
**Data Shape:** the renderer is a pure function over the discovery DTO — no I/O, no config reads. `handleModels` is the only async part: load global config → `collectModels` → branch on `config.json`. Text sections are joined with blank lines; global warnings are appended AFTER all backend sections, each prefixed `! `.

### Decisive source
```ts
// modelLine — per-row honesty hints, order fixed: id, variant collapse, fast, display name
function modelLine(m: CatalogModel): string {
  const parts: string[] = [m.id];
  if (m.variantCount && m.variantCount > 0) parts.push(`(+${m.variantCount} variant${m.variantCount === 1 ? '' : 's'})`);
  if (m.fast) parts.push('(fast available)');
  if (m.displayName && m.displayName !== m.id) parts.push(`— ${m.displayName}`);
  return parts.join(' ');
}
// formatBackend tail — overflow pointer names the EXACT scoped command:
    if (b.omittedCatalogModels > 0) {
      lines.push(`    +${b.omittedCatalogModels} more  (veda models ${b.backend} for the full inventory)`);
    }
  } else if (b.catalogSource === 'unavailable') {
    lines.push('  models   (unavailable)');
  }

  for (const w of b.warnings) {
    lines.push(`  ! ${w}`);
  }
// handleModels — the dual rendering branch:
export async function handleModels(config: ModelsConfig): Promise<void> {
  const globalConfig = await loadGlobalConfig();
  const result = await collectModels(config, globalConfig);

  if (config.json) {
    console.log(JSON.stringify(result, null, 2));
    return;
  }
  console.log(formatModelsText(result));
}
```

**Flow:** `collectModels` (offline-first, see `model-catalog-discovery.md`) returns one `ModelsResult`. JSON mode serializes it verbatim — warnings are already inside the document (`result.warnings` + per-backend `warnings[]`), so nothing extra is printed. Text mode maps each backend through `formatBackend`: header line with installed state, `default <model> (<human source label>)` via the `SOURCE_LABEL` table (unknown sources pass through raw rather than hiding), an `aliases` block with `[reasoning]` hints and `(your alias)` origin marks, a `models` block tagged `(catalogSource · completeness)` UNLESS unavailable (then a bare `models   (unavailable)` line), rows via `modelLine`, then the `+N more (veda models <backend> for the full inventory)` overflow pointer when the cap omitted rows, then per-backend `! warning` lines. Global warnings come last under a header that says `models (refreshed — live data for codex/agy)` when live probes ran.
**Invariant:** text and JSON render the SAME document — no information exists only in one rendering; warnings are data inside the result, never prose appended to stdout in JSON mode; every cap must be paired with an exact remedy command in the text view; unknown source labels degrade to raw passthrough instead of being dropped or invented.
**Probe:** `tests/commands/models.test.ts` (executed green at pin: 7 pass / 0 fail within the 39-test batch) — pins human source label `default  gpt-5.6-sol  (global config MODEL)`, alias reasoning + user-origin marks, variant-collapse + fast hints + `(curated · partial)` tag, the `+5 more  (veda models codex for the full inventory)` overflow pointer, `models   (unavailable)` + `! codex: no local cache` warning surfacing, not-installed mark, refreshed header. Coverage caveat: `handleModels` itself (the JSON branch) has no direct test — the tested seam is `formatModelsText`; the dispatch is four lines.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "veda", query: "formatModelsText formatBackend modelLine handleModels SOURCE_LABEL", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the one-document-two-renderings contract for any listing command with a `--json` mode: keep warnings/degradation labels INSIDE the structured result so the machine path stays clean, and make the human renderer add remedy-bearing furniture (overflow pointers naming the exact scoped command, humanized source labels, refreshed-data headers). Adapt the label table, indentation, and the cap-pointer command template to your CLI. Omit nothing behavioral; do not let the text renderer invent fields the DTO lacks (the `?? def.source` passthrough is the escape hatch). Keep the renderer pure so it is testable without any backend I/O.
