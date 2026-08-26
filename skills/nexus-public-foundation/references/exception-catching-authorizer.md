<!-- capsule-v2 -->
# Exception-catching authorizer — how do you keep one broken realm from breaking (or wrongly granting) an authorization decision across many realms?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d` (`ExceptionCatchingModularRealmAuthorizer.java`, `ExceptionCatchingModularRealmAuthorizerTest.java`); Codebase Memory `nexus-public`. **Question:** When several realms vote on every permission check, how do you contain a throwing realm so it neither crashes the request nor flips a deny into an allow?

## Per-realm exception containment with deny-by-default aggregation
**Path/Symbol:** `public/common/components/security/nexus-security/src/main/java/org/sonatype/nexus/security/authz/ExceptionCatchingModularRealmAuthorizer.java` (:38–299), decisive ladder `isPermitted(PrincipalCollection, String)` (:168–197).
**Signature:** `class ExceptionCatchingModularRealmAuthorizer extends ModularRealmAuthorizer`; overrides every `check*/has*/isPermitted*` variant; `RolePermissionResolver` injected via `Provider`.
**Data Shape:** in: PrincipalCollection + permission/role; out: boolean / boolean[] / void-with-exception; failure shape: realm exceptions swallowed → treated as abstain/false.

### Decisive source
```java
@Override
public boolean isPermitted(PrincipalCollection subjectPrincipal, String permission) {
  for (Realm realm : getRealms()) {
    if (!(realm instanceof Authorizer)) { continue; }
    try {
      if (((Authorizer) realm).isPermitted(subjectPrincipal, permission)) {
        return true;                                   // first grant wins
      }
    }
    catch (AuthorizationException e) {                 // realm said "can't decide"
      log.debug("Realm {} threw AuthorizationException", realm, e);
    }
    catch (RuntimeException e) {                       // realm is BROKEN
      log.warn("Realm {} threw unexpected exception...", realm, e);
    }
    // fall through to next realm
  }
  return false;                                        // no grant anywhere => deny
}
// same try/catch pattern in hasRole/isPermitted[]/hasRoles[] variants;
// checkPermission/checkRole convert !isPermitted into AuthorizationException("User is not permitted: ...")
```

**Flow:** security-system check → iterate realms in configured order → per realm, ANY exception (typed or runtime) logs and moves on → first affirmative grant short-circuits true → exhausted realms return false (or throw AuthorizationException only from the check* wrappers).
**Invariant:** a broken realm can never widen access (it only ever contributes false) and never propagates its failure to the caller; aggregation stays deny-by-default even when EVERY realm throws. The boolean-array variants keep positional alignment by defaulting each slot to false rather than aborting the batch.
**Probe:** `security/nexus-security/src/test/java/org/sonatype/nexus/security/authz/ExceptionCatchingModularRealmAuthorizerTest.java:ignoreRuntimeException` (:48–58) — single realm whose doGetAuthorizationInfo always throws RuntimeException; asserts `isPermitted` returns false across string/Permission/array/list variants instead of throwing.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nexus-public", query: "ExceptionCatchingModularRealmAuthorizer isPermitted ModularRealmAuthorizer", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-tier catch (AuthorizationException debug vs RuntimeException warn) with identical deny semantics, first-grant-wins ordering, and position-stable boolean arrays. Adapt Shiro's ModularRealmAuthorizer base to your authorization SPI. Omit nothing behavioral — but note the deliberate consequence: a persistently broken realm silently degrades to zero permissions, so alert on the warn log.
