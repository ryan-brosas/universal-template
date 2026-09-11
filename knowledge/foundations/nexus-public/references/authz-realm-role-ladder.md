<!-- capsule-v2 -->
# Authorization realm role ladder — how does an authorization-only realm turn principals into roles without ever authenticating?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d` (`AuthorizingRealmImpl.java`, `RolePermissionResolverImplTest.java`); Codebase Memory `nexus-public`. **Question:** How do you authorize subjects from many authentication realms through ONE Shiro realm that never authenticates, rejects disabled-realm principals, and caches per-principal permissions safely?

## Authorization-only Shiro realm with disabled-realm rejection and a per-principal permission cache
**Path/Symbol:** `public/common/components/security/nexus-security/src/main/java/org/sonatype/nexus/security/internal/AuthorizingRealmImpl.java:doGetAuthorizationInfo` (:120–184), `cleanUpRealmList` (:186–199), `isPermitted` (:201–228), event handlers (:230–253).
**Signature:** `protected AuthorizationInfo doGetAuthorizationInfo(final PrincipalCollection principals)`; `protected boolean isPermitted(final Permission permission, final AuthorizationInfo info)`; cache: `Cache<PrincipalCollection, Collection<Permission>>` expireAfterWrite(60min).softValues(), toggle via `${nexus.security.principal-permissions.cache.enabled}`.
**Data Shape:** in: primary-principal username + realm-name set; out: `SimpleAuthorizationInfo(roles)` / boolean imply-scan; failure: `AuthorizationException`.

### Decisive source
```java
setAuthenticationCachingEnabled(false); // we authz only, no authc done by this realm
setAuthorizationCachingEnabled(true);
...
public boolean supports(final AuthenticationToken token) { return false; }
...
// make sure the realm is enabled
if (!realmNames.contains(this.getName())) {
  for (Realm realm : realmSecurityManager.getRealms()) {
    if (realmNames.contains(realm.getName())) { foundRealm = true; break; }
  }
  if (!foundRealm) {
    throw new AuthorizationException("User ... belongs to a disabled realm(s)...");
  }
}
cleanUpRealmList(realmNames);                       // Nexus*Realm -> "default"
if (RoleMappingUserManager.class.isInstance(userManager)) {
  for (String realmName : realmNames) {             // per source realm
    try {
      for (RoleIdentifier r : ((RoleMappingUserManager) userManager).getUsersRoles(username, realmName)) {
        roles.add(r.getRoleId());
      }
    } catch (UserNotFoundException e) { /* trace only: no mappings is fine */ }
  }
}
else if (realmNames.contains("default")) { /* user-record roles or AuthorizationException */ }
```
Permission check with cache and invalidation:
```java
if (principalPermissionsCacheEnabled) {
  userPermissions = principalPermissionsCache.getIfPresent(principals);
  if (userPermissions == null) { userPermissions = this.getPermissions(info); principalPermissionsCache.put(principals, userPermissions); }
}
for (Permission perm : userPermissions) { if (perm.implies(permission)) return true; }   // linear implies() scan
return false;

@Subscribe public void on(final AuthorizationConfigurationChanged event) { invalidatePermissionsCache(); }
@Subscribe public void on(final SecurityContributionChangedEvent event)  { invalidatePermissionsCache(); }
@Subscribe public void on(final AuthorizationChangedDistributedEvent event) {
  if (EventHelper.isReplicating()) { invalidatePermissionsCache(); }                     // cluster twin
}
```

**Flow:** request subject → authorizer consults this realm LAST (forced by RealmManagerImpl) → principals' origin realms validated against enabled set → realm names normalized → roles resolved by ladder (role-mappings per realm → default user record → exception) → Shiro `getPermissions(info)` delegates to RolePermissionResolverImpl → result cached per principal for 60 min → linear `implies()` scan decides.
**Invariant:** this realm never authenticates (`supports`=false, authc off). A principal whose origin realm is currently DISABLED is refused authorization outright — enabling/disabling realms revokes access without touching users. Cache staleness is bounded by the three invalidation events; missing role-maps degrade to empty, never to grant.
**Probe:** `security/nexus-security/src/test/java/org/sonatype/nexus/security/authz/AuthorizingRealmImplTest.java:testAuthorization` (:109–124) — builds CPrivilege `app:config:read` + role + user, then asserts `hasRole("role")`, `isPermitted("app:config:read")` true and create/update/delete/ui variants false.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nexus-public", query: "doGetAuthorizationInfo cleanUpRealmList principalPermissionsCache AuthorizingRealmImpl", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt authorization-only realm with supports()=false, disabled-realm rejection, the role-ladder order (mappings → default record), and per-principal caching keyed on principals. Adapt Guava cache + Guava EventBus invalidation to your stack (keep all three triggers incl. cluster twin). Omit Sha1 credentials-matcher setup (dead code path when authc is disabled) if your framework has no such coupling.
