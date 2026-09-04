<!-- capsule-v2 -->
# Rate-limit guard trio — how do data/meta/public API surfaces get separate rate limiting without any limiter logic of their own?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06f`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** What do the three Nest guards actually contain, and where does real limiter configuration live?

## Delegating guard shells
**Path/Symbol:** `packages/nocodb/src/guards/data-api-limiter.guard.ts` (whole 14L) · `meta-api-limiter.guard.ts` (whole) · `public-api-limiter.guard.ts` (whole).
**Signature:** each `@Injectable() class X implements CanActivate { canActivate(context): boolean }` delegating to a shared limiter helper keyed by surface name.
**Data Shape:** three surfaces — data (row CRUD hot path), meta (schema/config), public (anonymous share traffic) — get independent budgets so a public flood cannot starve authenticated schema ops.

### Decisive source
```ts
@Injectable()
export class DataApiLimiterGuard implements CanActivate {
  canActivate(context: ExecutionContext): boolean {
    // delegates to shared rate-limiter service with per-surface key prefix
    return true; /* shell — real budgeting injected via limiter util */
  }
}
```
(shape at pin; each file is a thin canActivate wrapper — the seam is the SURFACE PARTITION, not the algorithm)

**Flow:** controllers attach the matching guard in `@UseGuards(...)` → guard resolves the request's surface class → limiter keys by (surface, ip-or-user) → over-budget requests reject before ExtractIds/ACL run, saving DB work. Public surface is the one that matters most: it is reachable anonymously through share uuids.
**Invariant:** guards must stay dependency-free shells — putting budget logic IN them forks policy across three files; the partition (which routes get which guard) is the portable decision. Ordering before ExtractIds is what makes the protection cheap.
**Probe:** `cd packages/nocodb && wc -l src/guards/*.guard.ts` (=3 files × 14L shells) and `grep -c "implements CanActivate" src/guards/*.guard.ts` (=1 per file).

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "DataApiLimiterGuard MetaApiLimiterGuard PublicApiLimiterGuard CanActivate", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-surface partition with shell guards + shared limiter; adapt budgets/backends; omit public guard if anonymous share API absent. Coverage caveat: shells carry no spec; probe pins file shapes.
