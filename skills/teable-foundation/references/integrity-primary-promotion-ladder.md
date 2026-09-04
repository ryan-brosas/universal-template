<!-- capsule-v2 -->
# Primary-field demote/promote ladder — how do you repair a broken primary without destroying downstream references?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** What is the safe ordering when the primary field itself is a lookup/unsupported type, or missing entirely?

## fixInvalidPrimary / fixMissingPrimary
**Path/Symbol:** `apps/nestjs-backend/src/features/integrity/link-integrity.service.ts:fixInvalidPrimary` (:1014–1132), `:fixMissingPrimary` (:1133–1196); detectors `checkInvalidPrimary` :201–245 (in-source incident note: "AI flipped Employee→lookup", T3367), `checkMissingPrimary` :246–265.
**Signature:** `fixInvalidPrimary(fieldId, issueType): Promise<IIntegrityIssue|undefined>`; `fixMissingPrimary(tableId)`.
**Data Shape:** Eligibility filter shared by both: `{deletedTime:null, isLookup:null, isConditionalLookup:null, lookupOptions:null, type:{in: PRIMARY_SUPPORTED_TYPES}}`.

### Decisive source
```ts
const result = await this.prismaService.$tx(async (prisma) => {
  // 1. Demote the bad primary first. Rename is deferred — only the formula fallback path
  //    needs to free up the original name for the new field.
  await prisma.field.update({ where: { id: oldField.id }, data: { isPrimary: null } });

  // 2. Defensive: if a separate valid primary already exists in the table, leave it alone.
  const existingValidPrimary = await prisma.field.findFirst({...});
  if (existingValidPrimary) return { kind: 'kept', field: existingValidPrimary };

  // 3. Prefer promoting an existing eligible candidate over creating a new formula field.
  const candidate = await prisma.field.findFirst({ ..., orderBy: { order: 'asc' } });
  if (candidate) { await prisma.field.update({ data: { isPrimary: true }, ...}); return {kind:'promoted',...}; }

  // 4. Fallback: rename bad primary to "<name> (before-fix)", then create + promote
  //    a formula field mirroring the old value.
  const legacyName = `${oldField.name} (before-fix)`;
  ...
});
```

**Flow:** Demote FIRST inside one outer transaction (inner service txs rejoin it, so any failure rolls back all partial mutations) → kept/promoted/formula-created three-way outcome. Missing-primary twin re-checks inside its own tx (race guard), promotes lowest-order eligible field, else creates a `SingleLineText` "Name". The bad field is ALWAYS preserved (renamed not deleted) so link previews' `options.lookupFieldId` and downstream lookups keep resolving.
**Invariant:** Never delete the broken primary and never leave zero primaries mid-repair; name collision is resolved by rename-only-in-fallback. The formula mirror (`{${oldField.id}}`) preserves displayed values for consumers of the old primary.
**Probe:** `grep -cF '(before-fix)' apps/nestjs-backend/src/features/integrity/link-integrity.service.ts` → 3.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "fixInvalidPrimary fixMissingPrimary promote formula", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt demote→kept/promoted/mirror ladder with outer-tx atomicity and reference-preserving rename; adapt eligibility predicate; omit the AI-incident comments.
