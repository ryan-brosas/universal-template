<!-- capsule-v2 -->
# Link exclusivity validation — how does teable enforce "one parent per child" for oneOne/oneMany links across batch-internal AND database-existing conflicts?

## group by host+key-shape → check 1 same-batch duplicates → check 2 per-group DB probes with expected-source comparison (update) vs not-in-self exclusion (insert)
**Path/Symbol:** `PostgresTableRecordRepository.ts` — `validateLinkExclusivityConstraints(context, db, constraints)` (:4628–4820, conflict predicate :4737–4740/:4779–4782), `validateInsertExclusivityConstraints` (:4834–5049, Check 1 :4850–4880, insert two-way probe :4966–4974, one-way `not in` self-exclusion :5003–5011). Tests: `PostgresTableRecordRepository.exclusivity.spec.ts` describe blocks (:79ff: oneOne duplicate :92, self-link allowed :105, oneMany batch dupes :144/:155).
**Signature:** inputs `LinkExclusivityConstraint{sourceRecordId, addedForeignRecordIds, usesJunctionTable, fkHostTableName, selfKeyName, foreignKeyName…}` / `InsertExclusivityConstraint{sourceRecordId, linkedForeignRecordIds,…}`.

### Decisive source
```ts
// update path — compare CURRENT holder against EXPECTED source:
const conflictingRecords = linkedRecords.filter(r => r.linked_to !== expectedSource);
// insert path — exclude our OWN sources so re-inserting your own children passes:
.where(group.selfKeyName, 'not in', [...group.sourceRecordIds])
```

**Flow:** group constraints by `two-way|junction :: fkHostTableName :: keyName :: foreignTableId` so N constraints cost ONE query → (insert only) reject same-batch cross-source duplicates in-memory first → run the grouped SELECT of current holders → update semantics flag any holder ≠ expected source; insert semantics flag ANY existing holder outside our own new sources.
**Invariant:** THE asymmetry a porter must copy: updates compare against an EXPECTED source (re-setting your own link is legal, someone else's isn't); inserts can't expect anything (rows don't exist yet) so they exclude self sources via NOT IN. Grouping keys differ subtly (`selfKeyName` vs `foreignKeyName`) because the two constraint types carry different key columns. Errors are i18n'd with hardcoded English fallback (`i18nOrFallback` :4614–4626 wraps `$t` in try/catch — translation failures must not mask the validation failure). Validation runs BEFORE snapshot capture begins (insert :1259, update :2146) so rejected writes leave no undo noise.
**Probe:** exclusivity.spec.ts :79–170 pins both checks' accept/deny matrices.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "validateInsertExclusivityConstraints validateLinkExclusivityConstraints one_many_duplicate", limit: 8 });
```
## Verdict
Adopt for exclusive-relation enforcement: batch-check first, grouped DB probes second, expected-vs-holder comparison on update vs self-exclusion on insert.
