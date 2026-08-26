<!-- capsule-v2 -->
# Group CRUD & team-name collision — how do ad-hoc groups (teams) differ from the five special role groups?

**Source:** grist-core MIT `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** Where does Grist support custom groups, and which invariants separate ROLE_TYPE from TEAM_TYPE?

## Team groups get global name-collision checks and type-locked overwrites; role groups are the fixed ACL vocabulary and may share names freely
**Path/Symbol:** `app/gen-server/lib/homedb/GroupsManager.ts`: `_throwIfTeamNameCollision` (:496–507), `createGroup` (:285–298), `overwriteRoleGroup` (:308–318) / `overwriteTeamGroup` (:328–339), `deleteGroup(id, expectedType?)` (:350–363), `_overwriteGroup` (:423–437), strict loaders `_getGroupsByIdsStrict` (:464–472).
**Signature:** `createGroup(descriptor: GroupWithMembersDescriptor, optManager?)`; descriptor = `{type: ROLE_TYPE|TEAM_TYPE, name, memberUsers?: number[], memberGroups?: number[]}`.
**Data Shape:** Collision query filters `groups.type = TEAM_TYPE` (+ `groups.id != :id` on overwrite) → 409 "Group with name ... already exists". Role-type creation with an existing name is ALLOWED (:135 test) — only team names are globally unique. Type change on overwrite → 400 "cannot change type of group".

### Decisive source
```ts
private async _throwIfTeamNameCollision(name: string, manager: EntityManager, existingId?: number) {
  const query = this._getGroupsQueryBuilder(manager)
    .where("groups.name = :name", { name })
    .andWhere("groups.type = :type", { type: Group.TEAM_TYPE });
  if (existingId !== undefined) {
    query.andWhere("groups.id != :id", { id: existingId });
  }
  const group = await query.getOne();
  if (group) { throw new ApiError(`Group with name "${name}" already exists`, 409); }
}
```
Delete with optional type pin:
```ts
const group = await this.getGroupWithMembersById(id, {}, manager);
if (!group || (expectedType && expectedType !== group.type)) {
  throw new ApiError(`Group with id ${id} not found`, 404);
}
await manager.createQueryBuilder().delete().from("group_groups")
  .where("subgroup_id = :id", { id }).execute();
await manager.remove(group);
```

**Flow:** member wiring uses STRICT id loaders that throw 404 listing every missing id — no silent partial groups; overwrite REPLACES membership wholesale via `Group.create({id: existing.id, ...})`. Delete first severs inbound nesting edges (`group_groups.subgroup_id`) then removes.
**Invariant:** `getMemberUserRoles` static (:64–77) folds a user's multiple group memberships into the STRONGEST role (`roles.getStrongestRole`) — order of aclRules is irrelevant. The delete's explicit `group_groups` cleanup exists because remove() doesn't cascade inbound edges; porters relying on ORM cascades leave dangling subgroup rows.

### Probe (direct tests)
`bash -c 'cd /mnt/hdd/utopia/inspo/platforms/grist-core && grep -n "should refuse to create a" app/gen-server/lib/homedb/GroupsManager.ts test/gen-server/lib/homedb/GroupsManager.ts | head -2'` → source :496 area + test :154.
`bash -c 'grep -c "memberUsers" app/gen-server/lib/homedb/GroupsManager.ts'` → ≥ 8.
Direct tests: `test/gen-server/lib/homedb/GroupsManager.ts` (423L: team create :115, members :124, same-name role allowed :135/:144, collision refused :154, overwrite families :171+).

### Retrieve
`codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"GroupsManager TEAM_TYPE ROLE_TYPE _throwIfTeamNameCollision overwriteTeamGroup","limit":8,"detail":"ids"}'`

**Verdict:** ADOPT — dual-group-type model (fixed ACL roles + free-form teams) with asymmetric uniqueness is directly reusable.
