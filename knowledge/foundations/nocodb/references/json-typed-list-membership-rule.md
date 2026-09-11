<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `packages/nocodb/src/dbQueryClient/aggregations/handlers/pg.handler.ts` :70–75 + :124–132 — JSON's presence in the FILLED list but absence from the SENTINEL list.

# Question
Why does JSON appear in CountFilled/CountUnique typed lists while CountEmpty handles it through a separate branch — and what does that imply for the sentinel?

## Path / Symbol
UITypes.JSON membership across pg common() branches.

## Data Shape
CountEmpty: dedicated `if ([UITypes.JSON].includes(column.uidt))` BEFORE the generic two-arm SQL (:70–75). CountFilled/CountUnique/PercentFilled/PercentUnique: JSON listed INSIDE the typed arrays (:98 etc.) so they take IS NOT NULL-only arms.

## Decisive source
pg.handler.ts:69–75 — the JSON branch exists because jsonb cannot be compared to ANY string sentinel (buildContext's enum comment establishes PG's typed-comparison failures); a `(x) = ''` predicate on jsonb is a runtime ERROR, not just wrong. So JSON can never ride the sentinel path and gets its own IS-NULL-only probe.
:87–106 — but CountFilled's typed array INCLUDES JSON (:98) precisely because once you drop the ''-arm, JSON behaves like every other typed column for filled/unique counting.
The pair of facts pins the design rule: **membership in the typed-filled list requires "IS NOT NULL alone is correct"; exclusion from the sentinel list requires "= sentinel comparison breaks"**. JSON satisfies both; Rating satisfies only the first (it CAN compare to 0, so it stays out of typed lists but keeps condnValue=0).

## Flow / Invariant
Porter test for each new column type on your platform: (1) does comparing its stored form to your empty-sentinel raise or misbehave? ⇒ sentinel-list decision. (2) is IS NOT NULL sufficient to mean "has content"? ⇒ typed-filled-list decision. Types answering differently on the two questions (JSON, Rating) are exactly the ones needing bespoke branches.

## Probe (direct test)
From repo root:
```
sed -n '69,76p' packages/nocodb/src/dbQueryClient/aggregations/handlers/pg.handler.ts | grep -c 'UITypes.JSON'   # => 1 dedicated branch
awk 'NR>=85 && NR<=107' packages/nocodb/src/dbQueryClient/aggregations/handlers/pg.handler.ts | grep -c 'JSON'   # => 1 inside filled list (:98)
grep -n 'Rating' packages/nocodb/src/dbQueryClient/aggregations/handlers/pg.handler.ts | head -3                 # => :52 buildContext 0-sentinel; NOT in filled lists
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"CountEmpty JSON UITypes branch","limit":3,"detail":"compact"}'
```
→ resolves the dedicated JSON branches across handlers line-exact.

## Verdict
**Adopt.** The two-question membership test is the portable rule; the JSON/Rating worked examples prove both branches.
