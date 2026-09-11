<!-- capsule-v2 -->
# Personal-view ACL attach — why are there TWO view bindings (`view` vs `shareViewType`) and what breaks if you merge them?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06f`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** How are personal/locked views attached to the request for ACL, and why must shared views never reach that attachment?

## Symbol-keyed request attachment with deliberate binding split
**Path/Symbol:** `packages/nocodb/src/middlewares/extract-ids/extract-ids.helpers.ts:VIEW_KEY/markPersonalViewIfNeeded/checkIsPersonalViewOwner` (:3, :11–:19, :25–:30) · `middlewares/extract-ids/extract-ids.middleware.ts` (:153–:158 comment, :229/:258/:441 attaches, :264–:276 + :610–:624 set `shareViewType` only).
**Signature:** `markPersonalViewIfNeeded(req, view)` stores under `Symbol.for('nc:view')` ONLY when `view.lock_type === Personal || Locked`.
**Data Shape:** `req[VIEW_KEY] = view` (symbol key — invisible to JSON logs/serialization); `shareViewType: ViewTypes | undefined` feeds `resolveShareAccessSource`.

### Decisive source
```ts
let view;
// See the note on the same binding in `legacyExtractIds` — kept apart from
// `view` so a shared view never reaches `markPersonalViewIfNeeded`.
let shareViewType: ViewTypes | undefined;
```
```ts
export function checkIsPersonalViewOwner(req: any): boolean {
  return (
    req[VIEW_KEY]?.lock_type === ViewLockType.Personal &&
    req[VIEW_KEY].owned_by === req.user?.id
  );
}
```

**Flow:** entity branches that resolved a real View call `markPersonalViewIfNeeded(req, view)` (three call sites in `use()`, one in `legacyExtractIds` :1017) → share-uuid branches deliberately assign ONLY `shareViewType = view.type` and leave `view` unset, so anonymous requests carry no VIEW_KEY → `AclMiddleware.aclFn` later reads `req[VIEW_KEY]` for the personal/locked gates (see acl-evaluation-ladder capsule) → `is_public`/`access_source` ride separately in `req.context`.
**Invariant:** attaching a locked/personal view to an ANONYMOUS (share-uuid) request would change its ACL evaluation class — the two bindings exist precisely to keep "which entity" (identity resolution) separate from "what ACL extras apply" (permission refinement). A porter merging them into one variable silently grants anonymous users personal-view gates or strips their shared-view access_source.
**Probe:** `cd packages/nocodb && grep -c "markPersonalViewIfNeeded(req" src/middlewares/extract-ids/extract-ids.middleware.ts` (=4 attach sites) and `grep -c "shareViewType = " src/middlewares/extract-ids/extract-ids.middleware.ts` (=4 assignments, never feeding VIEW_KEY).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "markPersonalViewIfNeeded checkIsPersonalViewOwner VIEW_KEY lock_type Personal", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt symbol-keyed request attachment and the two-binding split (entity var vs share-type var); adapt the permission lists (helpers :35–:139: PERSONAL_VIEW_MANAGEMENT_PERMISSIONS 21 entries, personalViewOwnerOnlyOps 6, editorPersonalViewOnlyPermissions 21+) to your permission vocabulary; omit ViewLockType values you don't support. Coverage caveat: helpers carry no dedicated spec; the lists are consumed by AclMiddleware probes below.
