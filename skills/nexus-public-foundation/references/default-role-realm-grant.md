<!-- capsule-v2 -->
# Default-role realm grant — how do you give every authenticated external user a baseline role without touching user records?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d` (`DefaultRoleRealm.java`, `DefaultRoleRealmTest.java`, `AnonymousHelper.java`); Codebase Memory `nexus-public`. **Question:** How can external/LDAP users — whose roles live outside your database — receive a configured baseline role at authorization time, while anonymous principals stay excluded?

## Authorization-time role injection guarded by the anonymous type marker
**Path/Symbol:** `public/common/components/security/nexus-default-role-plugin/src/main/java/org/sonatype/nexus/plugins/defaultrole/DefaultRoleRealm.java:doGetAuthorizationInfo` (:33–52), `maybeGrantRole`, authc rejection (:55–59); guard `security/nexus-security/src/main/java/org/sonatype/nexus/security/anonymous/AnonymousHelper.java:isAnonymous`.
**Signature:** `class DefaultRoleRealm extends AuthorizingRealm`; `void setRole(@Nullable final String role)`; `protected AuthorizationInfo doGetAuthorizationInfo(final PrincipalCollection principals)`.
**Data Shape:** in: any authenticated PrincipalCollection; out: `SimpleAuthorizationInfo` containing exactly one configured role, or null (abstain).

### Decisive source
```java
public static final String NAME = "DefaultRole";
private String role;                                        // injected from plugin config

@Override
protected AuthorizationInfo doGetAuthorizationInfo(final PrincipalCollection principals) {
  return maybeGrantRole(principals);
}

private AuthorizationInfo maybeGrantRole(final PrincipalCollection principals) {
  if (role != null) {
    // only attempt to apply default role if user is not anonymous
    if (!AnonymousHelper.isAnonymous(principals)) {         // instanceof AnonymousPrincipalCollection
      SimpleAuthorizationInfo info = new SimpleAuthorizationInfo();
      info.addRole(role);
      return info;
    }
  }
  return null;                                              // abstain: realm contributes nothing
}

@Override
protected AuthenticationInfo doGetAuthenticationInfo(final AuthenticationToken token) throws AuthenticationException {
  throw new UnsupportedOperationException();                // authorize-only realm
}
```

**Flow:** authorizer iterates realms in order → for each subject, DefaultRoleRealm returns one extra role id when configured and the principal is not anonymous → that role id expands through the normal RolePermissionResolverImpl tree walk → external users effectively inherit the baseline permission set with zero writes to user/role storage.
**Invariant:** unconfigured (`role == null`) ⇒ always abstain; anonymity exclusion is TYPE-based (marker principal collection), so renaming the anonymous account cannot leak the default role to it; authentication is structurally impossible in this realm (throws), keeping it purely additive at authorization time.
**Probe:** `security/nexus-default-role-plugin/src/test/java/org/sonatype/nexus/plugins/defaultrole/DefaultRoleRealmTest.java` — `testDoGetAuthorizationInfo_notConfigured` (:41–46) ⇒ null; `_authenticatedUser` (:49–55) ⇒ roles == {default-role}; `_anonymousUser` (:58–63) builds `AnonymousPrincipalCollection("anonymous","realm")` ⇒ null.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nexus-public", query: "DefaultRoleRealm maybeGrantRole AnonymousHelper isAnonymous", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt authorization-time baseline-role injection via an authorize-only realm plus type-marker anonymous exclusion. Adapt the single-string config to your policy store (and add more roles by returning a richer AuthorizationInfo). Omit the plugin health-check wrapper (`DefaultRoleHealthCheck`) unless you run Nexus-style capability health reporting.
