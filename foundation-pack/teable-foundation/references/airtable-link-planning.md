<!-- capsule-v2 -->
# Airtable link planning — which side owns a two-way link and why is every link created ManyMany first?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How does the planner pair Airtable's symmetric link fields, decide ownership/cardinality, and what must the importer NOT assume about "single" links?

## Inverse pairing + relationship decision
**Path/Symbol:** `apps/nestjs-backend/src/features/airtable-import/airtable-schema-mapper.ts`:`buildAirtableImportPlan` inverse sweep (:627–662) + `airtable-import.service.ts`:`decideRelationship` (:1138–1140).
**Signature:** `private decideRelationship(linkField: IPlannedLinkField): Relationship`.
**Data Shape:** each planned link carries `prefersSingle` (from `options.prefersSingleRecordLink`), optional `inverse {airtableFieldId, name, prefersSingle}` and `viewIdForRecordSelection`; the plan records which airtable field ids are realized as symmetric twins via `inverseFieldIds`.

### Decisive source
```ts
// Own the link from the single-link side so a one-to-many keeps its
// ManyOne cardinality regardless of table/field traversal order. Only
// flips when exactly one side prefers a single link; ties (both single
// or both multi) keep traversal order.
const fieldSingle = field.options?.prefersSingleRecordLink === true;
const inverseSingle = inverseField.options?.prefersSingleRecordLink === true;
const inverseOwns = inverseSingle && !fieldSingle;
inverseFieldIds.add(inverseOwns ? field.id : inverseField.id);
```
```ts
// Follows the relationship Airtable declares. One-to-* variants are not
// used because foreign-side uniqueness cannot be guaranteed before the
// records arrive; cells that violate a single link are truncated at fill
// time and reported.
private decideRelationship(linkField: IPlannedLinkField): Relationship {
  return linkField.prefersSingle ? Relationship.ManyOne : Relationship.ManyMany;
}
```

**Flow:** schema pass marks one field of each two-way pair as the owner (deterministic tie-break: single-link side wins) → non-inverse links become phase-2 planned fields; inverse twins are realized by RENAMING the symmetric field teable auto-creates (`renameSymmetricLinkField`, which must re-specify full options via convertField because a plain update drops the owning link) → at creation, cardinality is ManyOne only when that side prefers single, else ManyMany.
**Invariant:** Never create OneOne/OneMany up front — foreign-side uniqueness can't be guaranteed before data arrives. Airtable's "single link" is a soft per-cell preference, not enforced 1:1: oversized singles get relaxed to ManyMany before fill when data proved multi (`relaxOversizedSingleLinks`), else truncated-to-first with counts reported.
**Probe:** `grep -cF "inverseOwns" apps/nestjs-backend/src/features/airtable-import/airtable-schema-mapper.ts` returns 2; `grep -cF "symmetricFieldId" apps/nestjs-backend/src/features/airtable-import/airtable-import.service.ts` returns 4. Direct test: `airtable-schema-mapper.spec.ts` it('owns a one-to-many link on the single-link side, independent of table order') :241.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"teable","query":"decideRelationship relaxOversizedSingleLinks renameSymmetricLinkField","limit":5,"detail":"ids"}'
```

## Verdict
Adopt deterministic single-side ownership for symmetric relations and create-permissive/truncate-or-relax-later cardinality; adapt naming of relationships; omit teable's specific symmetric-field rename mechanics if the host has no auto-twin concept. Coverage caveat: none.
