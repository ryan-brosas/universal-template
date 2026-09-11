<!-- capsule-v2 -->
# maxInheritedRole inheritance algebra — how does "cap what children inherit from parents" work without copying permissions?

**Source:** grist-core MIT `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** Where is workspace/org inheritance actually stored, and how does lowering it protect the actor from lockout?

## Inheritance = parent's matching basic group nested in child group's memberGroups; moveInheritedGroups re-buckets by reverse-permissiveness; lowering to <owner auto-re-adds caller as owner
**Path/Symbol:** `app/gen-server/lib/homedb/GroupsManager.ts`: `_defaultGroups` (:95–116, ordered most→least permissive, nestParent flags), `moveInheritedGroups` (:139–176), `getMaxInheritedRole` (:263–277), `setInheritance` (:238–252), `getRoleFromPermissions` (:256–258); `HomeDBManager.ts`: `_moveInheritedGroups` private twin (:4617–4654) + owner-restoration (:2269–2274, :2346–2351).
**Signature:** `moveInheritedGroups(groups: NonGuestGroup[], inheritedGroups: Group[], dest?: roles.BasicRole | null): void`; `getMaxInheritedRole(res: Workspace | Document): roles.BasicRole | null`.
**Data Shape:** Only BASIC roles (owners/editors/viewers) are inheritable — guests/members filtered out up front. Storage probe: a child's `maxInheritedRole` is whichever top-level basic group has non-empty `memberGroups` (first hit walking most→least permissive, then `getEffectiveRole`). `dest === null` severs ALL inheritance; `dest === undefined` restores natural positions.

### Decisive source
```ts
const reverseDefaultNames = this.defaultBasicGroupNames.reverse();
// The destination must be a reserved inheritance group or null.
if (dest && !reverseDefaultNames.includes(dest)) {
  throw new Error("moveInheritedGroups called with invalid destination name");
}
...
// The destFunc maps from an inherited group to its required top-level group name.
const destFunc = (inherited: Group) =>
  dest === null ? null : reverseDefaultNames.find(sp => sp === inherited.name || sp === dest);
```
Actor-lockout protection at every delta call site:
```ts
this._moveInheritedGroups(groups, orgGroups, delta.maxInheritedRole);
if (delta.maxInheritedRole !== roles.OWNER) {
  // If the maxInheritedRole was lowered from 'owners', add the calling user
  // back as an owner so that their acl edit access is not revoked.
  userIdDelta = userIdDelta || {};
  userIdDelta[userId] = roles.OWNER;
}
```

**Flow:** create child → `createGroups(inherit)` + `setInheritance` wires each nestParent group's memberGroups to the parent's same-named group. Delta arrives → `moveInheritedGroups` resets memberGroups and re-buckets each inherited basic group into the destination-or-weaker slot → save groups → effective access computed later via `roles.getWeakestRole(orgMap, maxInheritedRole)` chains (see getDocAccess :2541).
**Invariant:** `defaultBasicGroupNames.reverse()` MUTATES the getter-fresh array (safe only because the getter maps a new array each call) — porters caching that array get silent order corruption. Inheritance lives in group nesting, NOT a column: reading it requires populated aclRules/groups/memberGroups or `getMaxInheritedRole` throws ("group X not found"). The auto-owner-restoration means lowering inheritance NEVER strands the actor — but also means the delta applied differs from the delta requested.

### Probe (direct tests)
`bash -c 'cd $REFERENCE_ROOT/platforms/grist-core && grep -n "moveInheritedGroups" app/gen-server/lib/homedb/GroupsManager.ts | head -1'` → :139.
`bash -c 'grep -c "_moveInheritedGroups" app/gen-server/lib/homedb/HomeDBManager.ts'` → ≥ 3.
Direct tests: `test/gen-server/ApiServerAccess.ts` :587–620 ladder (viewers cap → Kiwi still 403 rename → null restore), `test/gen-server/lib/homedb/GroupsManager.ts` group suites.

### Retrieve
`codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"maxInheritedRole moveInheritedGroups setInheritance memberGroups nestParent","limit":8,"detail":"ids"}'`

**Verdict:** ADOPT — nested-group inheritance with actor protection is the reusable alternative to permission-copying.
