<!-- capsule-v2 -->
# Handler contributor extension — how do plugins add handlers to EVERY repository route without core code or recipes changing?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d` (`nexus-repository-view/.../handlers/HandlerContributor.java`, `ContributedHandler.java`); Codebase Memory `nexus-public`. **Question:** What is the injection point that lets a plugin (webhooks, audit, analytics) wrap all repository traffic, and how is double-insert prevented?

## Reverse-order contributed-handler insertion guarded by a context marker
**Path/Symbol:** `public/common/components/nexus-repository-view/src/main/java/org/sonatype/nexus/repository/view/handlers/HandlerContributor.java:handle` (:43–58), `EXTENDED_MARKER` (:40–41); SPI: `ContributedHandler` (:27, one-line `handle(Context)`).
**Signature:** `public class HandlerContributor implements Handler`; ctor takes `@Lazy final List<ContributedHandler> contributedHandlers`; marker key = `LOCAL_ATTRIBUTE_PREFIX + HandlerContributor.class.getName() + ".extended"`.
**Data Shape:** contributed list injected by Spring in bean order; insertion walks it BACKWARDS so the final chain order matches the declared order.

### Decisive source
```java
public Response handle(@Nonnull final Context context) throws Exception {
  // Ensure the extra handlers are inserted only once, in the case that a handler higher
  // on the stack calls proceed() twice for some reason
  if (!isMarkedExtended(context)) {
    ListIterator<ContributedHandler> handlerIterator = contributedHandlers.listIterator(contributedHandlers.size());
    while (handlerIterator.hasPrevious()) {
      context.insertHandler(handlerIterator.previous());   // reverse walk => forward execution
    }
    markExtended(context);
  }
  return context.proceed();
}
```

**Flow:** the recipe places ONE `handlerContributor` in each route (see `recipe-assembly`). At dispatch it splices every contributed handler into the live chain via `Context.insertHandler` — before whatever would have run next — then proceeds. A boolean marker attribute in context attributes makes re-entry idempotent even when an outer handler calls proceed twice.
**Invariant:** this is THE stable plugin seam: core routes and format recipes never enumerate product handlers; plugins contribute and the contributor injects at runtime. Reverse iteration + insert-before-next yields declaration-order execution. The marker rides `local.attribute.*` so group fan-out copies keep the once-only guarantee across nested contexts.
**Probe:** `nexus-repository-view/src/test/java/org/sonatype/nexus/repository/view/handlers/HandlerContributorTest.java` — `addContributedHandlers` (:42) pins insertion; ordering verified against two stub contributors.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nexus-public", query: "HandlerContributor EXTENDED_MARKER ContributedHandler insertHandler", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the contribute-and-inject seam with reverse-order insertion and the once-per-request marker for any pipeline that must accept unbounded middleware from plugins without route edits. Adapt DI list injection to your container. Omit nothing — this capsule is the pattern.
