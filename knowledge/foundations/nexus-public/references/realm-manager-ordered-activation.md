<!-- capsule-v2 -->
# Realm manager ordered activation — how is the active realm set persisted, applied to Shiro in order, and kept working when admins disable every realm?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d` (`RealmManagerImpl.java`, `RealmManagerImplTest.java`); Codebase Memory `nexus-public`. **Question:** How do you persist an ordered list of active security realms, install them into the security manager, replicate changes across nodes, and guarantee the authorizing realm survives any configuration?

## Persisted ordered realm list with force-last authorizing realm and remote-event application
**Path/Symbol:** `public/common/components/security/nexus-security/src/main/java/org/sonatype/nexus/security/internal/RealmManagerImpl.java:resolveRealms` (:231–268), `maybeAddAuthorizingRealm` (:483–491), `on(RealmConfigurationEvent)` (:339–344), password/principal cache ladder (:347–391), `doStop` (:122–139).
**Signature:** `private List<Realm> resolveRealms()`; `private void maybeAddAuthorizingRealm(final List<String> realmIds)`; flag `${nexus.security.enableAuthorizationRealmManagement:false}`.
**Data Shape:** `RealmConfiguration { List<String> realmNames }` persisted via store; defaults from `@Qualifier("initial") Provider<RealmConfiguration>`; reads return copies.

### Decisive source
```java
// resolve configured realm components in stored ORDER
for (String configuredRealmId : configuredRealmIds) {
  Realm realm = availableRealms.get(configuredRealmId);          // Spring bean by qualifier id
  if (realm == null) {
    try { realm = (Realm) getClass().getClassLoader().loadClass(configuredRealmId).newInstance(); } // legacy fallback
    catch (Exception e) { log.error("Unable to lookup security realms", e); }                       // skip, don't fail boot
  }
  if (realm != null) { result.add(realm); }
}
...
private void maybeAddAuthorizingRealm(final List<String> realmIds) {
  if (!enableAuthorizationRealmManagement) {
    realmIds.remove(AuthorizingRealmImpl.NAME);   // remove-then-add: ALWAYS last
    realmIds.add(AuthorizingRealmImpl.NAME);
  }
}
...
@Subscribe
public void on(final RealmConfigurationEvent event) {
  if (!event.isLocal()) { changeConfiguration(event.getConfiguration(), false); }   // apply remote config WITHOUT re-saving
}
...
public void onEvent(final UserPasswordChanged event) {
  if (event.isClearCache()) { clearAuthcRealmCacheForUserId(event.getUserId()); }   // per-user authc eviction
}
```

**Flow:** doStart → load-or-default config → resolveRealms() (order = priority; authorizer appended last) → `realmSecurityManager.setRealms()` → local edits call setConfiguration (maybeAdd → save → install → post RealmConfigurationChangedEvent); remote nodes receive the event and apply with save=false so no echo loop.
**Invariant:** NexusAuthorizingRealm is present in every installed realm list even when admins remove all others (and stays stored in case the management flag flips later); unresolvable realm ids never abort boot; remote configuration events mutate memory but never re-persist. Cache hygiene: UserPrincipalsExpired clears ALL authc caches, AuthorizationConfigurationChanged clears ALL authz caches, password change evicts only that user's authc entry (distributed twin honored only for non-local + clearCache).
**Probe:** `security/nexus-security/src/test/java/org/sonatype/nexus/security/internal/RealmManagerImplTest.java` — `testOnStoreChanged_RemoteEvent` (:92–107) asserts a remote event re-posts RealmConfigurationChangedEvent with the new realm names; `testOnUserPasswordChanged_ClearCache` (:131–138) proves clearCache=false and non-local events touch no realm.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nexus-public", query: "resolveRealms maybeAddAuthorizingRealm RealmConfigurationEvent installRealms", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt persisted ordered realm ids resolved against DI beans with reflection fallback, the remove-then-add force-last guard for the authorizing realm, and apply-without-save semantics for replicated config events. Adapt Spring ApplicationContext bean lookup and the distributed-event bus to your stack. Omit the legacy class-name realm entries if you have no backward-compat burden (keep the skip-not-fail behavior regardless).
