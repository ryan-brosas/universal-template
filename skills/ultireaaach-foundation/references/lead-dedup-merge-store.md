<!-- capsule-v2 -->
# Dedup-or-merge lead store — how do you dedupe leads by URL and merge without clobbering existing fields?

**Source:** Ultireaaach `main@60bf4a3e478022df11ed2f04077d129f4f72cc60`; Codebase Memory `ultireaaach`. **Question:** two sources deliver the same person with partially different fields; what insert/update contract yields add-vs-merge semantics without data loss?

## Connected graph-selected seam
**Path/Symbol:** `packages/app/src/lead-store.ts:LeadStore.addLead` (115-152); identity index at line 98.
**Signature:** `addLead(lead: Partial<Lead>): { added: boolean; lead: Lead }`.
**Data Shape:** leads table with nullable profile fields, CSV `sources` column, FK collection_id, captured_at/enriched_at defaults; identity = `linkedin_url` backed by `CREATE UNIQUE INDEX ... ON leads(linkedin_url) WHERE linkedin_url IS NOT NULL`.

### Decisive source
```ts
if (li) {
  const existing = this.db.prepare("SELECT * FROM leads WHERE linkedin_url = ?").get(li);
  if (existing) {
    // Merge: update non-empty fields, preserve collection membership
    this.db.prepare(`
      UPDATE leads SET
        sources = sources || CASE WHEN instr(',' || sources || ',', ',' || ? || ',') > 0 THEN '' ELSE ',' || ? END,
        headline       = COALESCE(NULLIF(?, ''), headline),
        current_title   = COALESCE(NULLIF(?, ''), current_title),
        current_company = COALESCE(NULLIF(?, ''), current_company),
        location        = COALESCE(NULLIF(?, ''), location)
      WHERE id = ?`).get(/* new values..., existing.id */);
    return { added: false, lead: existing };   // merged, caller records 'merged' count
  }
}
// else INSERT ... RETURNING *  ->  { added: true, lead: row }
```
**Flow:** resolve identity by URL -> hit? fill-only-empty fields (NULLIF turns '' into NULL so COALESCE keeps the OLD value) + idempotent CSV source append (instr guard prevents duplicates) -> return existing row with added:false; miss? INSERT RETURNING with added:true. HTTP layer feeds the verdict into run counts recordAdded/recordMerged.
**Invariant:** merge NEVER overwrites a populated field with empty input; collection membership survives merges; sources list stays duplicate-free; the partial unique index makes the identity claim structural, not just query-enforced.
**Probe:** no dedicated unit test (coverage caveat). Live HTTP probe executed this pass against the running service: two POSTs of the same linkedin_url returned `{added:true}` then `{added:false}`, and GET /api/leads showed one row whose sources carried both tokens — see ultireaaach-work/verification.md.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ultireaaach", query: "addLead", limit: 5 });
// observed: total 1 -> ultireaaach.packages.app.src.lead-store.LeadStore.addLead Method packages/app/src/lead-store.ts 115-152
```

## Verdict
Adopt URL-identity + fill-only-empty merge + idempotent provenance CSV for any multi-source entity store. Adapt the identity column (email, external id) and which fields are fillable. Omit the RETURNING-based insert if your driver lacks it, but keep the add/merged verdict — run accounting depends on it.
