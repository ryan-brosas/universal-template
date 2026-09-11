<!-- capsule-v2 -->
# Undo scope resolution & dynamic stacking — how does an operation land on the right per-tab undo stack, and when does a rename go to base vs entity?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06f`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** How are undo stacks partitioned, and what decides sidebar-rename vs content-edit placement?

## Scope builders + ancestor pruning + sidebar-field dispatch
**Path/Symbol:** `packages/nocodb/src/command-registry/scope.ts:scopeBase/scopeView/getScopeAncestors/dynamicScope/SIDEBAR_FIELDS` (whole file 123L) · ScopeType union `command-registry/types.ts` (:427–:436).
**Signature:** `scopeBase(context): ScopeRef` THROWS on missing base_id; `getScopeAncestors(context, scope): Promise<ScopeRef[]>`; `dynamicScope(op, body, base, entity): ScopeRef`.
**Data Shape:** ScopeType = 'base'|'table'|'view'|'dashboard'|'workflow'|'script'|'interface'|'interfacePage'; persisted as `nc_operation_logs.scope_type/scope_id`; UndoRedoService filters `(user, tab, scope_type, scope_id)`.

### Decisive source
```ts
export async function getScopeAncestors(context, scope): Promise<ScopeRef[]> {
  const ancestors: ScopeRef[] = [];
  if (scope.type === 'view') {
    const view = await View.get(context, scope.id, true).catch(() => null);
    if (view?.fk_model_id) ancestors.push({ type: 'table', id: view.fk_model_id });
  }
  if (scope.type !== 'base' && context.base_id) ancestors.push({ type: 'base', id: context.base_id });
  return ancestors;
}
// Option-A dynamic scope:
return keys.every((k) => sidebar.has(k)) ? base : entity;
```
(:67–:82, :113–:123)

**Flow:** contracts resolve scope at FORWARD record time (after before() and body ran, so result+resolved.extra available) → inverse ops inherit the row's stored scope, never re-resolve → recordCommand calls getScopeAncestors to DELETE undone rows in ancestor scopes a new forward op would strand stale (undo lookup walks leaf-first, ancestors stay reachable — hence pruning, not blocking) → renames/reorders/nav-toggles (SIDEBAR_FIELDS sets for six *Update ops) land on the BASE stack while content edits land on the entity stack; empty body ⇒ base.
**Invariant:** enumerated-not-blacklisted sidebar fields is the safe-growth direction (new body fields default to entity scope); view→table ancestry must tolerate missing views (`.catch(() => null)` degrade to base-only); scopeBase throwing on missing base_id is deliberate — silently emitting `id: undefined` corrupts every future stack filter.
**Probe:** `cd packages/nocodb && grep -cE "^  [a-zA-Z]+Update: new Set" src/command-registry/scope.ts` (=6 ops with SIDEBAR_FIELDS entries) and `grep -n "scopeBase: context.base_id is required" src/command-registry/scope.ts` (:26 single throw site).

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "dynamicScope getScopeAncestors SIDEBAR_FIELDS scopeBase ScopeRef", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt forward-time scope stamping + ancestor-prune + enumerate-sidebar-fields dispatch; adapt stack partitions to your entity tree; omit interface/workflow/script scopes if absent from your host. Coverage caveat: CE ships builders but the recording consumer is EE — probe pins cover the CE half.
