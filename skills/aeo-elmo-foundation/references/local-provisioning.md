<!-- capsule-v2 -->
# Local provisioning — how do you bootstrap a single-user install without upserts?

**Source:** Elmo (aeo-elmo) MIT `main@da87272c`; Codebase Memory `ext-aeo-elmo`. **Question:** How are user/org/membership rows created so a second call fails loudly instead of corrupting state?

## Plain INSERTs + one-shot signup guard
**Path/Symbol:** `packages/lib/src/db/provisioning.ts:provisionLocalOrg` (L59–76), `countUsers` (L34–37), `slugify` (L87–95), `findUniqueBrandId` (L110–122), `ensureOrganization` (L156–176), `provisionUmbrellaOrg` (L183–203).
**Signature:** `provisionLocalOrg({userId}): {orgId}` (hardcoded org id `"default"`); `slugify(name): string`; `ensureOrganization({id,name}, conn?): Promise<void>`.
**Data Shape:** better-auth hooks gate signup: `user.create.before` REJECTS any signup when a user already exists (first-signup-only), and `user.create.after` provisions. No upsert, no existence checks in the happy path — "a second call is a bug and should fail at the database layer rather than silently rewriting rows".

### Decisive source
```ts
// Target the id explicitly: the early-return above already handles "org
// exists", so this only guards a concurrent insert of the same id (no-op).
// An untargeted onConflictDoNothing would also swallow a slug-unique
// collision, silently skip the insert, and leave the caller's brand FK to
// fail with a confusing error instead.
await conn.insert(organization).values({ id: input.id, … }).onConflictDoNothing({ target: organization.id });
```
And the ReDoS-scanner note: slugify trims leading/trailing hyphens by INDEX WALKS, not an `^-+|-+$` alternation regex, which trips ReDoS scanners on inputs like `"---"`.

**Flow:** umbrella-org path resolves the unique slug INSIDE the transaction so uniqueness-check and insert share one snapshot; same-named concurrent signups can still hit the slug unique index → failed signup, not duplicate org. Brand ids get `-2/-3` suffixes on collision with existing brands or reserved route slugs (`"new"`).
**Invariant:** reserved-slug set exists because brand ids appear directly in `/app/$brand` URLs; slug collisions must surface as human errors, never as silent skips.
**Probe:** `packages/lib/src/db/provisioning.test.ts` (GREEN in probe run; slug rules unit-tested without a DB).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-elmo", query: "provisionLocalOrg slugify findUniqueBrandId ensureOrganization", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt one-shot-INSERT philosophy + targeted-conflict guards; adapt slug reserved words to your routes; omit Auth0/umbrella paths if single-tenant.
