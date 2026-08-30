<!-- capsule-v2 -->
# dsh-mem0 per-call scoping — why do the same three params need two different casings?

**Source:** mem0 Apache-2.0 `main@7e09615`; Codebase Memory `mnt-hdd-utopia-inspo-memory-mem0`. **Question:** How does a tool accept optional per-call `userId`/`agentId`/`runId` overrides of a mount-time default when one backend endpoint wants snake_case and the other camelCase?

## Twin resolver pair
**Path/Symbol:** `integrations/dsh-mem0/src/scoping.ts` (`resolveSearchFilters` 26-38, `resolveAddParams` 41-53, shared `clean` :23).
**Signature:** `(params: EntityParams, defaultUserId: string) => Record<string, string>` where `EntityParams = { userId?: string; agentId?: string; runId?: string }`.
**Data Shape:** search returns `{ user_id, [agent_id], [run_id] }` (spread into `filters`, sent to the platform RAW); add returns `{ userId, [agentId], [runId] }` (top-level, run through the SDK's camel→snake converter).

### Decisive source
```ts
const clean = (v: string | undefined) => v?.trim() || undefined;

export function resolveSearchFilters(params, defaultUserId) {
  const filters = { user_id: clean(params.userId) ?? defaultUserId };
  const agentId = clean(params.agentId);
  if (agentId) filters.agent_id = agentId;
  ...
}
export function resolveAddParams(params, defaultUserId) {
  const out = { userId: clean(params.userId) ?? defaultUserId };
  if (agentId) out.agentId = agentId;   // camelCase: SDK converts top-level keys
  ...
}
```

**Flow:** trim each optional param (`clean`) → absent/blank falls back to configured `defaultUserId` for user_id/userId → agent/run scope keys are INCLUDED ONLY when non-blank (never emitted empty).
**Invariant:** The casing split is DELIBERATE, not incidental: search scope rides inside `filters` which the platform consumes raw → must be snake_case; add takes entity params TOP-LEVEL through the SDK's converter → must be camelCase. Keeping two explicit resolvers makes the asymmetry visible in code instead of load-bearing on a converter no-op. A porter who "unifies" them into one key-casing breaks one endpoint silently.
**Probe:** `integrations/dsh-mem0/tests/scoping.test.ts` (blank `"   "` userId falls back to default; blank agent_id OMITTED via `.not.toHaveProperty`; add-side camelCase shape) — green in the offline vitest suite.
**Retrieve:** search_graph project `mnt-hdd-utopia-inspo-memory-mem0` query `resolveSearchFilters` limit 3 → `integrations.dsh-mem0.src.scoping.resolveSearchFilters` scoping.ts 26-38 (rank 1 line-exact; twin query `resolveAddParams` also resolves rank 1).

## Verdict
Adopt the trim-normalize/fallback ladder and include-only-if-non-blank optional scope emission. Adapt key casing to YOUR split point: raw-passthrough payloads take snake_case, SDK-converter payloads take camelCase — mirror the sibling `integrations/pi-agent-plugin/src/memory/scoping.ts` only if you share its Scope enum shape (project/session/global), which dsh-mem0 deliberately does not.
