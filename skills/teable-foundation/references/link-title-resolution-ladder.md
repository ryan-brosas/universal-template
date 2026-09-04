<!-- capsule-v2 -->
# Link-title resolution ladder — how is a link cell's display title derived when the lookup field can't format it?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** What fallback chain produces `{id, title}` cells, and why must formatting failures never throw?

## extractLinkTitle / formatTitleWithField
**Path/Symbol:** `apps/nestjs-backend/src/features/calculation/link.service.ts:formatTitleWithField` (:213–224), `:extractLinkTitle` (:225–264); applied by `fixLinkCellTitle` (:507–547) and all four `updateForeignCellFor*` patchers.
**Signature:** `extractLinkTitle(value: unknown, field?: IFieldInstance): string | undefined`.
**Data Shape:** Returns the title string for `{id, title}` link-cell items; recursion over arrays with `, `-joining.

### Decisive source
```ts
private formatTitleWithField(field, value): string | undefined {
  try {
    const formatted = field.cellValue2String(value);
    if (typeof formatted === 'string' && formatted.trim().length > 0) return formatted;
  } catch {
    // Swallow formatting issues and fall back to generic extraction logic
  }
  return undefined;
}
```
```ts
if (typeof value === 'object') {
  const record = value as Record<string, unknown>;
  const candidateKeys = ['title', 'name', 'text', 'label', 'email'];
  for (const key of candidateKeys) { ... }
  const id = record.id;
  if (typeof id === 'string' && id.trim()) return id;   // LAST resort: the raw record id
}
```

**Flow:** Typed field formatter first (trim-nonempty gate) → string passthrough → number/boolean String() → array map+filter+join → object key ladder (`title,name,text,label,email`) → bare record id. Every arm tolerates absence; only a fully unresolvable value yields undefined (title omitted from the cell item).
**Invariant:** Title derivation is BEST-EFFORT BY CONTRACT — a formatter exception (broken formula primary in the foreign table, etc.) degrades to cruder titles rather than failing the whole link write; using the record id as terminal fallback keeps cells structurally valid so downstream OT ops never see malformed payloads.
**Probe:** `grep -cF "candidateKeys = ['title', 'name', 'text', 'label', 'email']" apps/nestjs-backend/src/features/calculation/link.service.ts` → 1; `grep -cF 'Swallow formatting issues' <same>` → present at :222.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "extractLinkTitle fixLinkCellTitle cellValue2String", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the degrade-don't-throw title ladder incl. id-as-final-fallback; adapt candidate keys to your schema; omit field-formatter integration if you have none.
