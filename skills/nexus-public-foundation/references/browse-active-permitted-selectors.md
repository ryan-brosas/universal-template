<!-- capsule-v2 -->
# Browse-active selectors — how do you answer "which of these stored expressions apply to *me* right now?" without evaluating any of them?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d`; Codebase Memory `nexus-public`. **Question:** How do you compute the subset of stored selectors a principal can actually reach, purely from role→privilege metadata plus repository/format scope?

## Role-tree walk → privilege filter → name intersection
**Path/Symbol:** `public/common/components/nexus-core/src/main/java/org/sonatype/nexus/internal/selector/SelectorManagerImpl.java:browseActive,getCurrentUser,getRoles,traverseRoleTree,matchesFormatOrRepository` (:310–394, 396–471).
**Signature:** `List<SelectorConfiguration> browseActive(final Collection<String> repositoryNames, final Collection<String> formats)`.
**Data Shape:** in: repository names + format names relevant to the current request; out: selector configs the current user holds via `RepositoryContentSelector` privileges; failure ⇒ empty list (fail-closed), never throws.

### Decisive source
```java
if (currentUser == null) return Collections.emptyList();          // fail-closed

List<String> roleIds = currentUser.getRoles().stream()
    .map(RoleIdentifier::getRoleId).collect(toList());

Set<String> privilegeIds = getRoles(roleIds, authorizationManager).stream()   // nested roles expanded
    .map(Role::getPrivileges).flatMap(Collection::stream).collect(Collectors.toSet());

List<String> contentSelectorNames = authorizationManager.getPrivileges(privilegeIds).stream()
    .filter(repositoryFormatOrNameMatcher(repositoryNames, formats))
    .map(this::getContentSelector)
    .collect(toList());

return browse().stream().filter(s -> contentSelectorNames.contains(s.getName())).collect(toList());

private void traverseRoleTree(final String roleId, final Map<String, Role> roleMap, final Set<String> results) {
  if (results.contains(roleId)) return;      // cycle-safe visited set
  Role role = roleMap.get(roleId);
  if (role == null) return;                  // missing/remote role tolerated
  results.add(roleId);
  role.getRoles().forEach(childId -> traverseRoleTree(childId, roleMap, results));
}
```

**Flow:** resolve default-source AuthorizationManager + current user (any failure ⇒ warn+empty) → user cache lookup keyed by principal + realm names (`javax.cache`, `CreatedExpiryPolicy`, TTL `nexus.shiro.cache.defaultTimeToLive:2m`; anonymous principals cached too via `AnonymousHelper.isAnonymous` acceptance) → collect user's direct role ids → expand through the role tree with a visited set over a snapshot-cached role map (cleared by role-change events) → union privileges of all reached roles → keep only `RepositoryContentSelectorPrivilegeDescriptor.TYPE` privileges whose `RepositorySelector` property matches requested repositories (`*` = all) or formats (`*-format` / all-formats) → intersect surviving selector names with the full browse list.
**Invariant:** no selector evaluation happens — applicability is decided entirely from role/privilege/repo metadata; unresolvable or missing pieces shrink the result toward empty rather than widening it.
**Probe:** `public/common/components/nexus-core/src/test/java/org/sonatype/nexus/internal/selector/SelectorManagerImplTest.java` — `browseActiveReturnsAllContentSelectorsForMatchingNestedRoles` (:172–184); `_ForNonMatchingFormats` (:209–222) ⇒ size 0; `_ReturnsNoContentSelectorsWhenAnonymousAccessDisabled` (:243–249); `browseActiveCachesRolesList` (:187–207, listRoles call-count ladder incl. event invalidation); `testUserIsTakenFromCache` / `_FromSystemIfNoValueInCache` / `Anonymous…` (:292–321).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nexus-public", query: "browseActive traverseRoleTree RepositoryContentSelectorPrivilegeDescriptor role privileges user", limit: 10 });
```
Live result (2026-08-26): 1,324 total hits; top rows = `traverseRoleTree` (:452–464), `SelectorManager.browseActive` interface (:59), impl (:310–349), `RepositoryContentSelectorPrivilegeDescriptor` ctor (:113–145).

## Verdict
Adopt the metadata-only reverse lookup with visited-set role expansion and fail-closed emptiness. Adapt the privilege-type/property keys and the wildcard grammar of your repository scope values. Omit the javax.cache user layer if your host already memoizes subjects. Consumers found via inbound trace: `RepositoryPermissionChecker.subjectHasAnyContentSelectorAccessTo*`, `ContentPermissionCheckerImpl.isPermitted`, SQL-search permission builder — port those next if you need request-time enforcement.
