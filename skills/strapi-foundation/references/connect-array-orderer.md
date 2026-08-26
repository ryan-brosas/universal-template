<!-- capsule-v2 -->
# Connect-array orderer — how do you honor positional `before/after` relation connects robustly?

**Source:** strapi MIT Expat (non-EE) `develop@1fd9d80ad5f0a2c97d09ce7529f5cd9fdb91ca2d`; Codebase Memory `strapi`. **Question:** Given an unordered array of `{ id, position: { before|after|end } }` connects plus existing DB relations, in what order must links be inserted, and which malformed inputs are rejected?

## Connect ordering seam
**Path/Symbol:** `packages/core/database/src/entity-manager/relations-orderer.ts:sortConnectArray` (37–143); consumer `relations-orderer.connect` (254–271).
**Signature:** `const sortConnectArray = (connectArr: Link[], initialArr: Link[] = [], strictSort = true) => Link[]`.
**Data Shape:** `Link = { id: ID, position?: { before?: ID, after?: ID, end?: true }, __component?: string }`; ids embed the uid for polymorphic/component relations so `(id, component)` pairs stay unique.

### Decisive source
```ts
if (adjacentRelId && relationsSeenInBranch[adjacentRelId]) {
  throw new InvalidRelationError('A circular reference was found in the connect array. ...');
}
...
if (existingRelation && (hasNoComponent || hasSameComponent)) {
  throw new InvalidRelationError(
    `The relation with id ${relation.id} is already connected. You cannot connect the same relation twice.`);
}
...
} else if (strictSort) {
  throw new InvalidRelationError(`... The relation with id ${adjacentRelId} needs to be connected first.`);
} else {
  sortedConnect.push({ id: relation.id, position: { end: true } }); // non-strict fallback
}
```

**Flow:** index all connects by id (newest-first spread keeps the *first* occurrence authoritative) → detect whether any anchor is missing from both initial (DB) and mapped arrays → if not needed, return input as-is → otherwise recursively `computeRelation`: resolve adjacent first (memoized via `computed`), push self after → output is a valid insertion order where every `before/after` target precedes its dependent.
**Invariant:** Cycle detection is *branch-scoped* (`relationsSeenInBranch`), so diamond-shaped but acyclic graphs sort fine; duplicates are rejected only for same-id-without-component or same-id-same-component; anchors satisfied by pre-existing DB relations never trigger recursion.
**Probe:** `packages/core/database/src/entity-manager/__tests__/sort-connect-array.test.ts` — four pinned behaviors: canonical reorder, reorder with initial DB relations, exact error message when an anchor doesn't exist, and the cycle/duplicate error messages.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "strapi", query: "regular relations connect delete links", qn_pattern: ".*regular-relations.*", limit: 25 });
```
Executed during pass 1: 308 total matches surfaced `relations-orderer.sortConnectArray` (37–143) and `relations-orderer.connect` (254–271) alongside the regular-relations family.

## Verdict
Adopt branch-scoped recursive topological resolution with component-aware duplicate rejection and a strict/non-strict switch for missing anchors. Adapt error types to your host's error hierarchy. Omit the component/polymorphic id-embedding convention unless your link table also carries component discriminators. Coverage: `no_recorded_issue` + `metadata_match` for `relations-orderer.ts`.
