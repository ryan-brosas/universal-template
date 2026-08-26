<!-- capsule-v2 -->
# Run Conditions — how do you decide "should this patch run on THIS page?" without deep if-trees?

**Source:** refined-github MIT `main@3bbe6088fe301d0d5cf1ae751a49307005762a68`; Codebase Memory `refined-github`. **Question:** What is the declarative predicate algebra that gates feature execution, and what are its truth-table edge cases?

## Connected graph-selected seam
**Path/Symbol:** `source/helpers/feature-utils.ts:` `shouldFeatureRun` (:26–37), `isFeaturePrivate` (:17–19), `RunConditions` (:8–15); `source/helpers/p-utils.ts:` `pSomeFunction` (:25–52), `pEveryFunction` (:54–81).
**Signature:** `shouldFeatureRun({asLongAs?: BooleanFn[], include?: BooleanFn[], exclude?: BooleanFn[]}): Promise<boolean>` where `BooleanFunction = () => boolean` (sync OR async).
**Data Shape:** three condition buckets: `asLongAs` = AND (every must be true), `include` = OR (at least one true), `exclude` = NOT-AND (no condition may be true). Defaults make absent buckets vacuous-pass: `asLongAs=[()=>true]`, `include=[()=>true]`, `exclude=[()=>false]`.

### Decisive source
```ts
return await pEveryFunction(asLongAs, c => c())
	&& await pSomeFunction(include, c => c())
	&& pEveryFunction(exclude, async c => !await c());
```
```ts
// p-utils: sync functions short-circuit BEFORE any promise machinery
for (const item of iterable) {
	const result = predicate(item);
	if (typeof result === 'boolean') {
		if (!result) return false;   // pEveryFunction: early sync exit
	} else {
		promises.push(result);
	}
}
if (promises.length === 0) return true;  // matches [].every(Boolean)
```

**Flow:** evaluate buckets sequentially (every → some → not-every) so sync conditions settle first; inside a bucket, sync predicates short-circuit immediately while async ones are collected and settled concurrently (`Promise.all` for every, first-truthy-wins race for some).
**Invariant:** `include: []` is FORBIDDEN upstream (`feature-manager.add` throws: empty include means "run nowhere") — but note the asymmetry: an *absent* include passes everything while an *empty* include throws; `exclude: []` would pass (vacuous). `isFeaturePrivate(id)` = `id.startsWith('rgh-')`: internal meta-features bypass the user's disable list entirely (checked in feature-manager before the skip branch).
**Probe:** `source/helpers/feature-utils.test.ts` pins the predicate algebra (`shouldFeatureRun` cases incl. async mixing); bucket semantics are exercised indirectly by every feature file's frontmatter (e.g. `batch-mark-files-as-viewed.tsx:106-114`: `include: [pageDetect.isPRFiles]`, `exclude: [pageDetect.isPRFile404, pageDetect.isPRCommit]`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", query: "shouldFeatureRun RunConditions asLongAs include exclude", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-bucket declarative gate verbatim for any plugin/pagelet system — it replaces ad-hoc `if (page === x && !mobile)` trees with composable predicates. Adapt the predicate vocabulary (here `github-url-detection` functions). Omit nothing: ~30 lines total, zero dependencies beyond p-utils. Direct test exists for the algebra; the empty-include throw is source-cited only.
