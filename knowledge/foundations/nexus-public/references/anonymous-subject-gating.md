<!-- capsule-v2 -->
# Anonymous subject gating — how do you bind a config-driven anonymous subject per request and restore the real one afterwards?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d` (`AnonymousFilter.java`, `AnonymousManagerImpl.java`, `AnonymousHelper.java`, `AnonymousManagerImplTest.java`, `AnonymousFilterTest.java`); Codebase Memory `nexus-public`. **Question:** How does a filter hand unauthenticated (and anonymous-typed) requests a fully-formed anonymous subject — enabled/disabled purely by config — without leaking it into the next request?

## Request-scoped subject swap with type-marker anonymity and replicated config
**Path/Symbol:** `public/common/components/security/nexus-security/src/main/java/org/sonatype/nexus/security/anonymous/AnonymousFilter.java:preHandle` (:77–107), `afterCompletion` (:109–118), `isAnonymousUser` (:121–127); `public/common/components/nexus-base/src/main/java/org/sonatype/nexus/internal/security/anonymous/AnonymousManagerImpl.java:buildSubject` (:167–186), `setConfiguration` (:139–158), `onStoreChanged` (:190–193); `.../anonymous/AnonymousHelper.java:isAnonymous`.
**Signature:** `protected boolean preHandle(ServletRequest, ServletResponse)`; `Subject buildSubject()`; config `{enabled, userId, realmName}` persisted via store + `@Qualifier("initial")` defaults.
**Data Shape:** marker principal: `AnonymousPrincipalCollection extends SimplePrincipalCollection` (anonymity = instanceof TYPE, not username string); dedupe cache: 100-entry ClientInfo LRU.

### Decisive source
```java
// preHandle
Subject subject = SecurityUtils.getSubject();
if ((subject.getPrincipal() == null || isAnonymousUser(manager, subject)) && manager.isEnabled()) {
  request.setAttribute(ORIGINAL_SUBJECT, subject);      // stash for restore
  subject = manager.buildSubject();
  ThreadContext.bind(subject);
  // 100-entry LRU of ClientInfo gates AnonymousAccessEvent emission
}
...
public void afterCompletion(...) {                        // ALWAYS restore
  Subject original = (Subject) request.getAttribute(ORIGINAL_SUBJECT);
  if (original != null) { ThreadContext.bind(original); }
}
// buildSubject: principals are the MARKER type, session creation disabled
PrincipalCollection principals = new AnonymousPrincipalCollection(model.getUserId(), model.getRealmName());
return new Subject.Builder().principals(principals).authenticated(false).sessionCreationEnabled(false).buildSubject();
// anonymity check is TYPE-based:
public static boolean isAnonymous(@Nullable final PrincipalCollection principals) {
  return principals instanceof AnonymousPrincipalCollection;
}
// replicated config: apply remote events without re-saving
if (!EventHelper.isReplicating()) { store.save(model); }
this.configuration = model;
eventManager.post(new AnonymousConfigurationChangedEvent(model));
```

**Flow:** request arrives with no principal (or an already-anonymous one) AND anonymity enabled → stash current subject as request attribute → bind freshly built anonymous subject (marker principals, not authenticated, no session) → downstream code sees a normal Subject → afterCompletion rebinds the stashed original regardless of outcome.
**Invariant:** the anonymous subject never survives its request (attribute-scoped restore); disabling anonymity instantly stops binding while existing behavior degrades gracefully; anonymity detection is the principal-collection TYPE so renaming the anonymous user cannot break it; config changes replicate via events where remote nodes apply without re-saving (no store echo).
**Probe:** `security/nexus-security/src/test/java/org/sonatype/nexus/security/anonymous/AnonymousFilterTest.java:testBuildSubjectWhenIsAnonymousUser` (:57–67) — enabled manager + configured anonymous userId ⇒ preHandle calls buildSubject; `nexus-base/src/test/java/org/sonatype/nexus/internal/security/anonymous/AnonymousManagerImplTest.java:testHandleConfigurationEvent_FromRemoteNode` (:111) pins remote-apply semantics.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "nexus-public", query: "AnonymousFilter buildSubject AnonymousPrincipalCollection ORIGINAL_SUBJECT", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the stash-bind-restore filter shape, the principal-collection type marker for anonymity, session-creation-disabled subjects, and the bounded ClientInfo dedupe before emitting access events. Adapt ThreadContext/Shiro Subject.Builder to your framework's request-scoped identity holder. Omit the JMX @ManagedAttribute exposure unless you run a management plane.
