<!-- capsule-v2 -->
# Proposal rows for suggested changes — how does Grist persist "comparison snapshots" between two docs with per-destination sequence numbers?

**Source:** grist-core MIT `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** Where do proposal shortIds come from, and how do retractions/applies update status without races?

## MAX(short_id)+1 per destination doc under transaction; orUpdate upsert on (src,dest); applied status stamps appliedAt in the same statement
**Path/Symbol:** `app/gen-server/lib/homedb/HomeDBManager.ts`: `setProposal` (:3456–3509), `updateProposalStatus` (:3511–3527), `getProposals` (:3529–3547) / `getProposal` (:3549–3560).
**Signature:** `setProposal({srcDocId, destDocId, comparison: DocStateComparison, retracted?})` → normalized ApiProposal; `updateProposalStatus(destDocId, shortId, status: ProposalStatus)`.
**Data Shape:** proposals = `{srcDocId, destDocId, comparison json, shortId int (per-dest), status json ({status:"applied"}|{status:"retracted"}|{}), updatedAt, appliedAt}`; listing orders `short_id DESC`, joins src+dest docs with creator logins.

### Decisive source
```ts
const maxRow = await manager.createQueryBuilder()
  .from(Proposal, "proposals")
  .select("MAX(proposals.short_id)", "max")
  .where("proposals.dest_doc_id = :docId", { docId: options.destDocId })
  .getRawOne<{ max: number }>();
const shortId = (maxRow?.max || 0) + 1;
...
.orUpdate(["comparison", "status", "updated_at", "applied_at"], ["src_doc_id", "dest_doc_id"])
.execute();
```
Status stamping:
```ts
.set({
  status,
  updatedAt: timestamp,
  ...(status.status === "applied") ? { appliedAt: timestamp } : {},
})
.where("shortId = :shortId", { shortId })
.andWhere("destDocId = :destDocId", { destDocId })
```

**Flow:** setProposal also flips the DESTINATION doc's options to `mayHaveProposals: true` via updateDocument riding the PREVIEWER user + specialPermit (system-level write bypassing caller permissions) — all inside ONE transaction so the flag can't be left dangling. Retraction at creation passes `retracted:true`; apply/retract later go through updateProposalStatus.
**Invariant:** shortIds are scoped PER DESTINATION doc (human-friendly "#5" within a doc's suggestions tab), not globally — a porter keying them globally breaks the UI contract; the composite where-clause on status updates reflects that scoping. MAX()+1 inside the transaction is safe only under the backend's serialization guarantees (sqlite global; postgres relies on this low-frequency path).

### Probe (direct tests)
`bash -c 'cd $REFERENCE_ROOT/platforms/grist-core && grep -n "mayHaveProposals" app/gen-server/lib/homedb/HomeDBManager.ts | head -2'` → :3492.
`bash -c 'grep -rn "orUpdate" app/gen-server/lib/homedb/HomeDBManager.ts'` → single call site :3481.
Direct tests: proposal suites under test/ (grep setProposal callers — comparisons module).

### Retrieve
`codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"setProposal Proposal short_id orUpdate updateProposalStatus mayHaveProposals","limit":8,"detail":"ids"}'`

**Verdict:** ADAPT — niche feature but a clean recipe for per-scope human sequence numbers with upsert semantics.
