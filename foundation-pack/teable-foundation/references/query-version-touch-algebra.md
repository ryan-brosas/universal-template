<!-- capsule-v2 -->
# Version-touch reconstruction — how does a repository report per-field version changes when the visitor only records WHICH fields were touched?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** After N statements each bump a version, how do you synthesize the old→new chain for realtime/undo consumers without reading intermediate states?

## Touch-order × final-version algebra
**Path/Symbol:** `packages/v2/adapter-repository-postgres/src/repositories/PostgresTableRepository.ts`: `updateOne` (:913-997: visitor-compiled statement execution, then version collection), `loadFieldVersionsByIds`/:999-1031 + view twin :1033-1066 (post-update SELECT with notFound on ANY missing id), `buildFieldVersionChanges` (:1068-1091), `buildViewVersionChanges` (:1093-1116).
**Signature:** `buildFieldVersionChanges(touchOrder: ReadonlyArray<string>, finalVersions: Map<string,number>): FieldVersionChange[]` where `oldVersion = max(finalVersion - totalCount + currentIndex, 0)`, `newVersion = oldVersion + 1`.
**Data Shape:** touchOrder = occurrence list (same id may repeat); missing final row ⇒ domainError.notFound (fail loud — table state diverged from expectation).

### Decisive source
```ts
return fieldVersionTouchOrder.map((fieldId) => {
  const totalCount = countByFieldId.get(fieldId) ?? 0;
  const finalVersion = finalVersionByFieldId.get(fieldId) ?? 0;
  const currentIndex = indexByFieldId.get(fieldId) ?? 0;
  indexByFieldId.set(fieldId, currentIndex + 1);
  const oldVersion = Math.max(finalVersion - totalCount + currentIndex, 0);
  return { fieldId, oldVersion, newVersion: oldVersion + 1 };
});
```

**Flow:** mutateSpec.accept(updateVisitor) compiles ordered UPDATE statements → execute sequentially in the ambient tx → collect which fields/views the visitor touched and in what order → read back FINAL versions once → reconstruct the step-by-step change list arithmetically.
**Invariant:** Versions are assumed to increment by exactly 1 per touching statement starting from (final − touches); the Math.max(…,0) floor absorbs legacy rows whose version started below the touch count instead of emitting negative versions. The reconstruction happens AFTER execution inside the same tx, so the read-back sees exactly the statements this call applied.
**Probe:** no dedicated spec at this HEAD for build*VersionChanges (helpers spec covers mapping); parse_partial flag = line 1224. Coverage caveat recorded.
**Coverage caveat:** version-change algebra verified by source reading; direct unit specs absent upstream.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "buildFieldVersionChanges loadFieldVersionsByIds updateOne TableMetaUpdateVisitor", limit: 6, fields: ["signature","name","file"] });
```

## Verdict
Adopt the arithmetic reconstruction (it avoids N round trips and intermediate snapshots); adapt if your increments aren't unit-step; keep the fail-loud missing-id check — silent zeros would corrupt undo chains.
