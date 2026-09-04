<!-- capsule-v2 -->
# View router + handler chain — how does request dispatch stay interceptor-shaped while letting any handler insert more handlers mid-flight or replay the request?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d` (`nexus-repository-view/.../view/Router.java`, `Context.java`); Codebase Memory `nexus-public`. **Question:** How do I build a per-repository route table whose handler chain is mutable during execution (insert-before-next, re-proceed) without breaking position?

## First-match router over a ListIterator chain with retained position
**Path/Symbol:** `public/common/components/nexus-repository-view/src/main/java/org/sonatype/nexus/repository/view/Router.java:dispatch` (:54–70), `findRoute` (:146–153); `nexus-repository-view/.../view/Context.java:proceed` (:88–104), `insertHandler` (:109–114), `replayable` (:120–137), `start` (:181–188).
**Signature:** `Response dispatch(final Repository repository, final Request request, @Nullable final Context existingContext)`; `Response proceed()`; `void insertHandler(final Handler handler)`; `Context replayable()`.
**Data Shape:** `handlers = new ArrayList<>(route.getHandlers()).listIterator()` — the route's list is COPIED at start so runtime insertion never mutates shared state. `LOCAL_ATTRIBUTE_PREFIX = "local.attribute."` marks attributes that survive context copies.

### Decisive source
```java
// Router — first match wins, else DefaultRoute
private Route findRoute(final Context context) {
  for (Route route : routes) {
    if (route.getMatcher().matches(context)) return route;
  }
  return defaultRoute;
}

// Context — interceptor proceed with position retention
public Response proceed() throws Exception {
  checkState(handlers != null, "Context not started");
  checkState(handlers.hasNext(), "End of handler chain");
  Handler handler = handlers.next();
  try {
    return handler.handle(this);
  } finally {
    // retain handler position in-case of re-proceed
    if (handlers.hasPrevious()) { handlers.previous(); }
  }
}

// Context — splice a handler in front of "next" mid-chain
public void insertHandler(final Handler handler) {
  handlers.add(handler);
  handlers.previous();
}
```

**Flow:** dispatch builds a fresh Context (copying only `local.attribute.*` from an existing one for group fan-out), finds first matching route, and `start(route)` seeds the iterator then calls `proceed()`. Each handler either short-circuits a Response or calls `context.proceed()` to invoke the next — interceptor style with pre/post phases around it. `insertHandler` appends then steps back so the NEXT `proceed()` hits the inserted handler exactly once.
**Invariant:** the finally-block `previous()` is what makes re-`proceed()` safe (a handler may call proceed twice to retry downstream); `replayable()` buffers the payload into `BytesPayload` because streams are single-shot — group repositories MUST replay when fanning out to members. Handler list copied at start protects other requests sharing the same configured route.
**Probe:** no dedicated upstream test pins proceed/insert semantics directly (`HandlerContributorTest.java` exercises insert via the contributor seam); coverage caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nexus-public", query: "Context proceed insertHandler replayable findRoute", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt copied-list ListIterator dispatch, position-retained proceed, insert-before-next splicing, and buffered replay before fan-out. Adapt matcher types (Action/Suffix/logic combinators) to your routing DSL. Omit Rapture-facing IndexHtmlForwardHandler specifics.
