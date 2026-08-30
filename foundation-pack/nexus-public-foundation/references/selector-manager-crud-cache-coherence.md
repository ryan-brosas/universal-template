<!-- capsule-v2 -->
# Selector manager CRUD + cache coherence — how do you cache compiled user expressions and keep them correct across CRUD, cluster replication, and referential integrity?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d`; Codebase Memory `nexus-public`. **Question:** What does a manager around stored expressions owe you beyond pass-through CRUD — compile caching, invalidation on every mutation path, and delete protection when the expression is referenced elsewhere?

## Soft caches, four-event invalidation ladder, privilege-scan delete guard
**Path/Symbol:** `public/common/components/nexus-core/src/main/java/org/sonatype/nexus/internal/selector/SelectorManagerImpl.java:browse,delete,on(SelectorConfigurationEvent),on(SelectorConfigurationChangedEvent),evaluate,isInUse` (:91–483).
**Signature:** `List<SelectorConfiguration> browse()`; `void delete(final SelectorConfiguration)`; `boolean evaluate(final SelectorConfiguration, final VariableSource) throws SelectorEvaluationException`.
**Data Shape:** three independent caches: volatile `SoftReference<List<SelectorConfiguration>>` browse snapshot; Guava softValues `LoadingCache<SelectorConfiguration, Selector>` (compiled); `Map<String,Role>` rolesCache. Config = {name,type,description,attributes[`expression`]}.

### Decisive source
```java
private static final SoftReference<List<SelectorConfiguration>> EMPTY_CACHE = new SoftReference<>(null);

public void delete(final SelectorConfiguration configuration) {
  if (isInUse(configuration)) {                                   // BEFORE any store call
    throw new IllegalStateException(
        "Content selector " + configuration.getName() + " is in use and cannot be deleted");
  }
  store.delete(configuration);
}

private boolean isInUse(final SelectorConfiguration configuration) {
  return securitySystem.listPrivileges().stream()
      .filter(p -> RepositoryContentSelectorPrivilegeDescriptor.TYPE.equals(p.getType()))
      .anyMatch(p -> p.getPrivilegeProperty(P_CONTENT_SELECTOR).equals(configuration.getName()));
}

@Subscribe @AllowConcurrentEvents
public void on(final SelectorConfigurationEvent event) {          // local CRUD
  cachedBrowseResult = EMPTY_CACHE;
  rolesCache = Collections.emptyMap();
  selectorCache.invalidateAll();
}

@Subscribe
public void on(final SelectorConfigurationChangedEvent event) {   // remote node (cluster-replicated)
  cachedBrowseResult = EMPTY_CACHE;
  rolesCache = Collections.emptyMap();
  selectorCache.invalidateAll();
}
```

**Flow:** create/update/delete write through to the store (create maps `DuplicateKeyException` → field validation error "name must be unique") → every local or remote selector mutation clears all three caches so the next `browse()` re-reads storage as truth → `evaluate` compiles lazily through `selectorFactory.createSelector(type, attributes.get(EXPRESSION))` into the soft cache and wraps ANY failure as named `SelectorEvaluationException` → deletes are refused while a repository content-selector privilege still names the selector.
**Invariant:** storage is always authoritative — both cache layers are memory-sensitive and fully invalidated rather than diff-merged, and the same handler shape covers local events and replicated remote events; referential integrity is enforced by scanning live privileges before the store sees a delete.
**Probe:** `public/common/components/nexus-core/src/test/java/org/sonatype/nexus/internal/selector/SelectorManagerImplTest.java` — `testDelete_FailsWhenContentSelectorIsUsedByPrivilege` (:264–272) asserts IllegalStateException AND `verifyNoInteractions(store)`; `testDelete_Succeeds` (:251–262); `testEvaluate_True/_False/_InvalidSelectorType` (:145–161, junk type ⇒ SelectorEvaluationException); `findByNameReturnsEmptyOptional/ExpectedSelector` (:274–289).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nexus-public", query: "SelectorManagerImpl isInUse delete in use selectorCache invalidate browse", limit: 10 });
```
Live result (2026-08-26): 1,423 total hits; top rows = `isInUse` (:477–482), `delete` (:216–226), `browse(String)` (:159–164), `selectorCache` field (:107), plus UI-side `SelectorComponentTest.testDelete_blobStoreInUse`.

## Verdict
Adopt: full-invalidate-on-mutation over clever incremental cache maintenance, soft references so cache pressure can't OOM the server, wrap-any-failure evaluation errors carrying the selector name, and delete-blocking via reference scan of consuming entities. Adapt the privilege-scan to whatever entity type references your stored expressions in your host. Omit the separate remote-event handler only if your bus delivers remote mutations as ordinary local events.
