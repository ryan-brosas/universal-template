<!-- capsule-v2 -->
# Airtable cell conversion contract — how do hostile computed cells become safe teable values?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** What does each converter kind accept, how are error-marker cells and NUL bytes handled, and what is the collaborator email-matching contract?

## convertAirtableCellValue + convertCollaboratorCellValue
**Path/Symbol:** `apps/nestjs-backend/src/features/airtable-import/airtable-record-converter.ts`:`convertAirtableCellValue` (:55–116), `convertCollaboratorCellValue` (:129–153), `extractLinkedRecordIds` (:156–171).
**Signature:** `convertAirtableCellValue(converter: IAirtableCellConverter, raw: unknown): unknown` — returns `undefined` when the cell must stay empty.
**Data Shape:** raw cells come from `cellFormat=json` + `returnFieldsByFieldId=true`; computed fields can carry `{"error":"#ERROR!"}` or `{"specialValue":"NaN"}` objects instead of values.

### Decisive source
```ts
const isErrorValue = (value: unknown): boolean =>
  typeof value === 'object' && value !== null && !Array.isArray(value) &&
  ('error' in value || 'specialValue' in value);
...
case 'boolean':
  return raw === true ? true : undefined;   // false cells are omitted by Airtable
case 'snapshotNumber': {
  if (isErrorValue(raw)) return undefined;
  if (Array.isArray(raw)) return toNumber(raw[0]);
  return toNumber(raw);
}
```
```ts
const user = collaborator.email ? usersByEmail.get(collaborator.email.toLowerCase()) : undefined;
if (user) resolved.push({ id: user.id, title: user.name, email: user.email });
else droppedCount++;
```

**Flow:** every converter strips `\0` from strings (Postgres rejects NUL) → error/specialValue markers ⇒ undefined (empty cell, never a crash) → arrays collapse to first element for scalar snapshots; scalars wrap into arrays for array converters (`stringArray` accepts a bare value) → `user`/`attachment` converters return undefined here because they need external context (space-collaborator map / CDN transfer) and are handled by the importer → collaborators resolve by case-insensitive EMAIL match against the target space's members with unmatched counted as `droppedCount` → link ids extract from strings or `{id}` objects.
**Invariant:** Conversion never throws — worst case is an empty cell plus a counted issue. Checkbox `false` never writes (Airtable omits false cells entirely). Collaborators that aren't space members are DROPPED and reported per field, not guessed into ids.
**Probe:** `grep -cF "specialValue" apps/nestjs-backend/src/features/airtable-import/airtable-record-converter.ts` returns 2. Direct tests: `airtable-record-converter.spec.ts` it('passes strings through and strips NUL bytes') :8, it('drops unmatched collaborators and counts them') :78.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"teable","query":"convertAirtableCellValue convertCollaboratorCellValue extractLinkedRecordIds","limit":5,"detail":"ids"}'
```

## Verdict
Adopt never-throw cell normalization with error-marker detection and count-and-report drops for any ETL cell plane; adapt the converter vocabulary; omit Airtable's specific marker spellings if the source differs. Coverage caveat: file indexed but its spec carries one parse_partial line (:11) — content verified against working tree.
