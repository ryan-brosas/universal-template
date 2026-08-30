<!-- capsule-v2 -->
# ACL role-permission inheritance — how does acl.ts compile per-role include/exclude tables at MODULE LOAD, and what breaks if you treat it as static data?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06f`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** Why do roles appear to grant permissions they never declared, and which invariants are enforced by boot-time self-checks?

## Boot-time inheritance + five self-throwing validators
**Path/Symbol:** `packages/nocodb/src/utils/acl.ts:rolePermissions` (:330–:660) · `permissionScopes`/`roleScopes` (:10–:33) · validation+inheritance block (:676–:798) · `sourceRestrictions` export (:801–:823).
**Signature:** module top-level `Object.values(roleScopes).forEach(...)` mutates `rolePermissions` IN PLACE before any import sees it; SUPER_ADMIN is the string `'*'` (wildcard), guest `{}`.
**Data Shape:** each role = `{include?: Record<perm,true>} | {exclude?: Record<perm,true>} | '*'`; include/exclude mutually exclusive (validator #5 throws).

### Decisive source
```ts
// inherit include permissions within scope (role order)
Object.values(roleScopes).forEach((roles) => {
  let roleIndex = 0;
  for (const role of roles) {
    if (roleIndex === 0) { roleIndex++; continue; }   // lowest role starts empty-handed
    if (rolePermissions[role] === '*') continue;
    if (rolePermissions[role].include) {
      Object.assign(rolePermissions[role].include,
        rolePermissions[roles[roleIndex - 1]].include);   // accumulate from previous role
    }
    roleIndex++;
  }
});
// inherit exclude permissions within scope (REVERSE role order) — mirrored block :763-783
```
(:742–:760)

**Flow:** validators run in order — duplicate-permission-within-scope throw (:677–:696), role-must-belong-to-a-scope throw, scope-table-exists throw, permission-not-in-role-scope throw (:699–:739), include∧exclude throw (:786–:793) → include inheritance accumulates UP the roleScopes arrays (org/workspace/base) → exclude inheritance walks REVERSED arrays → org VIEWER collapses to CREATOR's table (`rolePermissions[VIEWER] = rolePermissions[CREATOR]`, :797, EE pattern) → the SAME mutated object is read by AclMiddleware.aclFn.
**Invariant:** inheritance direction asymmetry is the trap — includes cascade from lower→higher privilege so a higher role implicitly grants everything below it; excludes cascade from HIGHER→lower so a restriction declared on a privileged role propagates down. Porters who copy the table without the load-order block ship roles missing ~80% of their effective permissions. Duplicate-permission detection exists precisely because Object.assign would otherwise silently mask a double declaration.
**Probe:** `cd packages/nocodb && grep -c "throw new Error(" src/utils/acl.ts` (=6 boot-time validators incl. duplicate-permission ×2) and `sed -n '801,825p' src/utils/acl.ts | grep -c ": true"` (=20 source-restricted permissions: 2 schema-readonly + 18 data-readonly).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "rolePermissions permissionScopes sourceRestrictions SourceRestriction SCHEMA_READONLY", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt boot-time compilation with self-throwing validators and the two-direction inheritance; adapt role sets/scope tables to your product; omit the EE viewer-collapse only if you have no collapsed-tier pattern. Coverage caveat: pure data+init module, no spec; probes count-pinned.
