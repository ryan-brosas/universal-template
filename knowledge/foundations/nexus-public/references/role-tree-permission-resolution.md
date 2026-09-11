<!-- capsule-v2 -->
# Role-tree permission resolution — how do you expand nested role IDs into permissions safely under cycles and missing references?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d` (`RolePermissionResolverImpl.java`, `RolePermissionResolverImplTest.java`); Codebase Memory `nexus-public`. **Question:** How does one resolve a role ID (which may nest other roles arbitrarily) into a permission set without stack overflow on cycles, without repeated store hits for missing roles, and without failing when references dangle?

## Iterative BFS role expansion with cycle guard, soft caches, and a bounded negative cache
**Path/Symbol:** `public/common/components/security/nexus-security/src/main/java/org/sonatype/nexus/security/internal/RolePermissionResolverImpl.java:resolvePermissionsInRole` (:127–186), `descriptor` (:190–204), `permission` (:207–226), caches (:78–92).
**Signature:** `Collection<Permission> resolvePermissionsInRole(final String roleString)`; NFC: `CacheBuilder.newBuilder().maximumSize(${security.roleNotFoundCacheSize:100000}).build()`.
**Data Shape:** in: role id; out: `LinkedHashSet<Permission>` (stable order); internal: CRole {roles[], privileges[]}, CPrivilege {type,id}; failure shape: missing refs skipped silently.

### Decisive source
```java
final Set<Permission> permissions = new LinkedHashSet<>();
final Deque<String> rolesToProcess = new ArrayDeque<>();
final Set<String> processedRoleIds = new HashSet<>();      // cycle guard
rolesToProcess.add(roleString);
while (!rolesToProcess.isEmpty()) {
  final String roleId = rolesToProcess.removeFirst();
  if (processedRoleIds.add(roleId)) {
    if (roleNotFoundCache.getIfPresent(roleId) != null) { continue; }   // negative cache
    cachedPermissions = rolePermissionsCache.getIfPresent(roleId);
    if (cachedPermissions != null) { permissions.addAll(cachedPermissions); continue; }
    try {
      final CRole role = configuration.readRole(roleId);
      rolesToProcess.addAll(role.getRoles());              // nested roles -> queue, not recursion
      for (String privilegeId : role.getPrivileges()) {
        Permission permission = permission(privilegeId);
        if (permission != null) { permissions.add(permission); }
      }
    }
    catch (NoSuchRoleException e) {
      roleNotFoundCache.put(roleId, "");                   // remember the miss
    }
  }
}
rolePermissionsCache.put(roleString, permissions);
...
private Permission permission(final String privilegeId) {
  Permission permission = permissionsCache.getIfPresent(privilegeId);
  if (permission == null) {
    try {
      CPrivilege privilege = configuration.readPrivilege(privilegeId);
      PrivilegeDescriptor descriptor = descriptor(privilege.getType());
      if (descriptor != null) { permission = descriptor.createPermission(privilege); permissionsCache.put(privilegeId, permission); }
    } catch (NoSuchPrivilegeException e) { /* skip dangling privilege */ }
  }
  return permission;
}
```
Invalidation mirrors the realm's triggers:
```java
@Subscribe public void on(final AuthorizationConfigurationChanged event)     { invalidate(); }
@Subscribe public void on(final SecurityContributionChangedEvent event)      { invalidate(); }
@Subscribe public void on(final AuthorizationChangedDistributedEvent event)  { if (EventHelper.isReplicating()) invalidate(); }
```

**Flow:** role id → check role cache → dequeue-walk the role tree (nested roles queued, visited-set prevents infinite loops) → per role, each privilege id resolves via type-matched `PrivilegeDescriptor.createPermission` → union accumulates in insertion order → result cached per queried root role.
**Invariant:** no recursion (cycles and deep nesting cannot overflow); a missing role costs exactly ONE store read ever (bounded NFC), then is silently ignored; an unknown privilege *type* warns once per resolution and yields no permission; all three caches clear together on any authorization-config or security-contribution change (cluster twin included). Deny-by-default: empty set means "no permissions".
**Probe:** `security/nexus-security/src/test/java/org/sonatype/nexus/security/internal/RolePermissionResolverImplTest.java:resolvePermissionsInRole_roleNotFoundCache` (:55–78) — mocks readRole to always throw NoSuchRoleException; asserts readRole called ONCE across four resolutions, twice after firing `AuthorizationConfigurationChanged`, then cached again.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nexus-public", query: "resolvePermissionsInRole roleNotFoundCache PrivilegeDescriptor createPermission", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the iterative visited-set walk, the three-tier cache design (permission / role-result / bounded negative), and silent-skip semantics for dangling references. Adapt Guava caches + event bus to your infra; keep the NFC bounded so attackers cannot grow it with junk role ids. Omit the LinkedHashSet ordering guarantee if your permission checks are order-insensitive.
