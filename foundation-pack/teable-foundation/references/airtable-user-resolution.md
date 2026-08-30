<!-- capsule-v2 -->
# Airtable user-field resolution — why must collaborators map against the BASE's space, not the caller's?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** Which space's membership is the correct mapping target for collaborator cells during an into-existing-base import, and what is the lookup key contract?

## getSpaceUsersByEmail
**Path/Symbol:** `apps/nestjs-backend/src/features/airtable-import/airtable-import.service.ts`:`getSpaceUsersByEmail` (:748–773).
**Signature:** `private async getSpaceUsersByEmail(spaceId: string): Promise<Map<string, IResolvedSpaceUser>>`.
**Data Shape:** two queries — active space collaborators (`resourceType: CollaboratorType.Space`, `principalType: PrincipalType.User`) → their live users (`deletedTime: null`); keyed by LOWERCASED email → `{id, name, email}`.

### Decisive source
```ts
// Resolve user fields against the base's actual space, not ro.spaceId —
// for an existing-base import the two can differ (ro.spaceId is optional
// there), and the base's members are the correct mapping target.
const usersByEmail = await this.getSpaceUsersByEmail(base.spaceId);
```
```ts
return new Map(
  users.map((user) => [
    user.email.toLowerCase(),
    { id: user.id, name: user.name, email: user.email },
  ])
);
```

**Flow:** once per import (not per table) after the target base exists → collaborator rows join to non-deleted users → map consumed per cell by case-insensitive email match in the converter; unmatched collaborators increment the field's dropped count and become a `valuesDropped` issue at end of table.
**Invariant:** The mapping universe is the BASE's space membership — importing into an existing base ignores any caller-passed spaceId for identity resolution. Emails are the join key because Airtable collaborator cells carry emails while teable user cells need ids. Soft-deleted users and deleted collaborators never match.
**Probe:** `grep -cF "getSpaceUsersByEmail" apps/nestjs-backend/src/features/airtable-import/airtable-import.service.ts` returns 2 (call site + definition); direct test coverage via `airtable-record-converter.spec.ts` it('matches collaborators by email case-insensitively') :69.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"teable","query":"getSpaceUsersByEmail usersByEmail CollaboratorType.Space","limit":5,"detail":"ids"}'
```

## Verdict
Adopt resolve-once-per-import membership maps keyed on lowercased email for any cross-system identity migration; adapt principal queries to host schema; omit teable's collaborator enums. Coverage caveat: none.
