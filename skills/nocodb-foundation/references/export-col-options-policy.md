<!-- capsule-v2 -->
# ColOptions remap policy — which link/lookup/formula option keys get id-mapped on export, which survive verbatim, and which are stripped?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f751366`; Codebase Memory project `nocodb`. **Question:** Column colOptions carry raw db ids in a dozen shapes (junction refs, lookup targets, formula `{{colId}}` bodies, select options) — what is the per-key rewrite policy that keeps an import from dangling?

## Path/Symbol
`packages/nocodb/src/modules/jobs/jobs/export-import/export.service.ts:ExportService.serializeModels` — the `Object.entries(column.colOptions)` switch at lines 296–379.

**Signature:** inline: for each column after `getColOptions`, iterate `Object.entries(colOptions)` and dispatch per key.

**Data Shape:** keys fall into four classes: REMAP (all fk_* relation/lookup/rollup/qr/barcode/display/webhook/script refs incl. junction internals `fk_mm_child_order_column_id` etc.); PRESERVE (`fk_workspace_id`, `fk_integrations_id`, `model` — workspace-scoped integrations only); TRANSFORM (`output_column_ids` CSV-of-ids → map each; `formula` → alias-rewrite `formula_raw` + idMap the `{{…}}` body; `options[]` → strip row identity); STRIP (`id`, timestamps, `fk_column_id`).

### Decisive source
```ts
case 'output_column_ids':   // comma-separated ids inside ONE string
  column.colOptions[k] = ((v as string)?.split(',') || []).map(id => idMap.get(id)).join(',');
  break;
case 'formula':
  if (column.uidt === UITypes.Button) break;      // Button formulas keep {{titles}}
  column.colOptions['formula_raw'] = column.colOptions[k]?.replace(/\{\{.*?\}\}/gm, m => {
    const col = model.columns.find(c => c.id === m.slice(2, -2)); return `{${col?.title}}`; });
  column.colOptions[k] = column.colOptions[k]?.replace(/(?<={{).*?(?=}})/gm, m => idMap.get(m));
  break;
case 'options': for (const o of column.colOptions['options']) { delete o.id; delete o.fk_column_id; } break;
case 'id': case 'created_at': case 'updated_at': case 'fk_column_id':
  delete column.colOptions[k]; break;
```

**Flow:** runs before view/hook/comment serialization so every later filter/sort rewrite sees already-mapped column ids. Unknown keys pass through untouched (default no-op), so adding new option types doesn't need exporter changes unless they embed ids.

**Invariant:** formulas carry TWO representations and they must diverge deliberately: `formula_raw` is rewritten to `{colTitle}` aliases (human-readable, Button-type exempt) while `formula` has its `{{colId}}` body mapped to destination ids — porters who rewrite only one produce formulas that display right but evaluate wrong. Select options must lose row identity (`id`, `fk_column_id`) or inserts collide with existing rows. The pg `cdf` quote-trim (lines 382–394): if a default value has an ODD number of single quotes, cut at the last one — a dialect-specific escape bug guard, not general quoting.

**Probe:** no unit test upstream. Source-grounded probe: `export.service.ts:298-317` (remap class list incl. five `fk_mm_*` junction keys), `:318-324` (preserve class), `:325-329` (output_column_ids split-map-join), `:348-365` (formula dual rewrite + Button exemption), `:382-394` (pg cdf odd-quote trim). Cross-check: `import.service.ts` reconstructs against these exact key names.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "serializeModels colOptions formula_raw output_column_ids cdf", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt the four-class remap policy (remap/preserve/transform/strip) and the dual formula representation; adapt the key list to your schema; omit the pg cdf trim unless porting postgres sources. Coverage caveat: no in-repo unit tests; source-grounded.
