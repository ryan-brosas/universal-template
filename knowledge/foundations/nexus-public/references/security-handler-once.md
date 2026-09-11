<!-- capsule-v2 -->
# Security handler authorize-once — why doesn't a group repository re-run permission checks for every member repository it fans out to?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d` (`nexus-repository-services/.../repository/security/SecurityHandler.java`); Codebase Memory `nexus-public`. **Question:** How is authorization memoized across the nested dispatch that happens when a group repository traverses into member repositories?

## Request-scoped authorized marker consulted before every ensurePermitted
**Path/Symbol:** `public/common/components/nexus-repository-services/src/main/java/org/sonatype/nexus/repository/security/SecurityHandler.java:handle` (:54–68), `AUTHORIZED_KEY = "security.authorized"` (:41).
**Signature:** `Response handle(@Nonnull final Context context)` — implements `org.sonatype.nexus.repository.view.handlers.SecurityHandler`; per-repository `SecurityFacet` does the actual check.
**Data Shape:** marker lives in `context.getAttributes()` (the AttributesMap that `local.attribute.*` copies propagate across nested contexts).

### Decisive source
```java
public Response handle(@Nonnull final Context context) throws Exception {
  SecurityFacet securityFacet = context.getRepository().facet(SecurityFacet.class);

  // we employ the model that one security check per request is all that is necessary, if this handler is in a nested
  // repository (because this is a group repository), there is no need to check authz again
  if (context.getAttributes().get(AUTHORIZED_KEY) == null) {
    securityFacet.ensurePermitted(context.getRequest());
    context.getAttributes().set(AUTHORIZED_KEY, true);
    if (loginsCounterHandler != null) {
      context.insertHandler(loginsCounterHandler);
    }
  }
  return context.proceed();
}
```

**Flow:** first entry on a request ⇒ run the repository's `ensurePermitted`, set `security.authorized=true` in context attributes, optionally splice the login-counter handler in front of "next". Any later invocation — e.g. the same route shape inside member repositories reached via group traversal, where attributes were copied over — sees the marker and skips straight to `proceed()`.
**Invariant:** authorization granularity is PER REQUEST, not per repository: once any facet authorized the request, nested repositories inherit that decision through the copied attribute map (see `view-router-chain`). A failed `ensurePermitted` throws before the marker is ever set, so denials are never laundered.
**Probe:** `nexus-repository-services/src/test/java/org/sonatype/nexus/repository/security/SecurityHandlerTest.java` — `testHandle_alreadyAuthorized` (:67), `testHandle_loginsCounterHandlerIsNull` (:74).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nexus-public", query: "SecurityHandler AUTHORIZED_KEY ensurePermitted", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the request-scoped authorization memo keyed in copied context attributes whenever your pipeline nests/fans out after an authz point. Adapt SecurityFacet resolution and the login-counter hook to your host. Omit the qualifier-nullable analytics handler wiring.
