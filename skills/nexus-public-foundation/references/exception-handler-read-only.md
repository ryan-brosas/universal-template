<!-- capsule-v2 -->
# Exception handler read-only mapping — which exceptions become 400/404/503, and how is frozen-mode detected even through wrapped or renamed drivers?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d` (`nexus-repository-view/.../handlers/ExceptionHandler.java`); Codebase Memory `nexus-public`. **Question:** Where does the handler chain convert domain failures into HTTP statuses, and why does it sniff exception class NAMES for a database-specific type?

## Typed ladder with frozen/read-only detection by class-name substring
**Path/Symbol:** `public/common/components/nexus-repository-view/src/main/java/org/sonatype/nexus/repository/view/handlers/ExceptionHandler.java:handle` (:36–76), `readOnly` (:78–86).
**Signature:** `Response handle(@Nonnull final Context context)` — prototype-scoped (`@Scope(SCOPE_PROTOTYPE)`) Handler wrapping `context.proceed()` in the typed catch ladder.
**Data Shape:** IllegalOperationException→400; InvalidContentException→400 on PUT else 404; FrozenException (direct, as cause, or by class-name match)→503 read-only; everything else rethrown.

### Decisive source
```java
catch (InvalidContentException e) {
  if (PUT.equals(context.getRequest().getAction())) {
    return HttpResponses.badRequest(e.getMessage());
  }
  return HttpResponses.notFound(e.getMessage());   // GET of bad content = not found
}
catch (FrozenException e) {
  return readOnly(context, e);
}
catch (Exception e) {
  if (e.getCause() instanceof FrozenException) {
    return readOnly(context, e);
  }
  String exceptionName = e.getClass().getSimpleName();
  if (exceptionName.contains("OModificationOperationProhibitedException")
      || exceptionName.contains("OWriteOperationNotPermittedException")) {
    return readOnly(context, e);                    // driver-level write ban → read-only mode
  }
  throw e;
}
```

**Flow:** proceed inside try; each domain exception maps to a response with a warn log carrying method+path; unknown exceptions propagate (the servlet layer owns 500s). Read-only mode is recognized three ways because writes can be refused at different layers: core FrozenException, any exception whose CAUSE is one, or an OrientDB-driver prohibition recognized only by simple-name substring — deliberately tolerant of the class being absent from compile-time deps.
**Invariant:** PUT-vs-GET asymmetry for invalid content (client error vs missing resource). The name-sniff exists so the view layer never hard-depends on the storage backend's exception types — port this pattern when your storage engine's exceptions aren't on the classpath.
**Probe:** no dedicated upstream ExceptionHandlerTest in-tree; behavior pinned indirectly via repository ITs. Coverage caveat recorded; deterministic probe = assert the three-way frozen detection and PUT/GET split on stub handlers.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nexus-public", query: "ExceptionHandler FrozenException OModificationOperationProhibitedException readOnly", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the mapping ladder + cause-walk + name-based driver-exception tolerance. Adapt the exception taxonomy to your domain. Omit the OrientDB class names once your storage refuses writes through its own typed exception you can depend on.
