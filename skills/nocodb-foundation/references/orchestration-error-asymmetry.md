<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `packages/nocodb/src/dbQueryClient/cross-db-utils/aggregate.ts` :136–153 + `bulk-aggregate.ts` :180–183 — the twin catch blocks.

# Question
Why does single aggregation rethrow after logging while bulk aggregation swallows into `{}`?

## Path / Symbol
`aggregate()` catch; `bulkAggregate()` catch.

## Signature
```ts
// aggregate:  catch (e) { logger?.error?.(e.message, e.stack); throw e; }
// bulkAggregate: catch (err) { logger?.error?.(err.message, err.stack); return {}; }
```

## Data Shape
Both log via optional `logger?` (the orchestrations are curried with an OPTIONAL second arg — most callers pass none, so errors surface through the throw/return channels only).

## Decisive source
aggregate.ts:150–153 — rethrow preserved so a failed view-footer aggregate surfaces as an API error (the service entry has no fallback rendering for partial stats).
bulk-aggregate.ts:180–182 — swallow-to-{} because the widget footer renders N buckets and one failing bucket (e.g. a column dropped mid-flight) should blank THAT widget, not fail the whole dashboard payload. The design pairs with the up-front validation at :33–46 which moves USER-INPUT errors outside this swallowing reach (they 400 before the try).
The pair is the visible half of NocoDB's error doctrine also seen in ce-stub/EE work: user-input errors validate loudly up front; runtime per-item failures degrade per item; whole-request integrity failures rethrow.

## Flow / Invariant
Porter decision rule to copy: classify failure sources BEFORE choosing catch semantics — malformed input ⇒ throw early outside any swallowing scope; per-item runtime failure ⇒ item-scoped empty result; orchestration-level impossibility ⇒ rethrow. Applying one catch policy everywhere either leaks 500s to dashboards or hides real breakage behind empty stats.

## Probe (direct test)
From repo root:
```
sed -n '150,153p' packages/nocodb/src/dbQueryClient/cross-db-utils/aggregate.ts | grep -c 'throw e'        # => 1
sed -n '180,182p' packages/nocodb/src/dbQueryClient/cross-db-utils/bulk-aggregate.ts | grep -c 'return {}' # => 1
grep -c 'logger?\.' packages/nocodb/src/dbQueryClient/cross-db-utils/aggregate.ts packages/nocodb/src/dbQueryClient/cross-db-utils/bulk-aggregate.ts   # => 1 + 1
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"logger error stack catch orchestration","limit":3,"detail":"compact"}'
```
→ resolves both catch regions.

## Verdict
**Adopt.** The asymmetric-catch pairing is deliberate; preserve it when porting the two orchestrations together.
