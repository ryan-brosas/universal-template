<!-- capsule-v2 -->
# Variable source resolver chain — how do you feed namespaced context data into an expression engine lazily and read-only?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d`; Codebase Memory `nexus-public`. **Question:** How should expression variables be supplied so evaluation touches only the variables the expression actually uses, resolves through prioritized sources, and can never mutate its inputs?

## Ordered resolver chain + lazy memoized JEXL context
**Path/Symbol:** `public/common/components/nexus-selector/src/main/java/org/sonatype/nexus/selector/VariableSource.java:get,getVariableSet` (:26–63); `JexlSelector.java:asJexlContext` (:66–88); `PropertiesResolver.java` (:32–85); `ConstantVariableResolver.java:sourceFor` (:27–64).
**Signature:** `Optional<Object> get(final String variable)`; `Set<String> getVariableSet()`; `VariableResolver { Optional<Object> resolve(String); Set<String> getVariableSet(); }`.
**Data Shape:** in: ordered `List<VariableResolver>`; namespaced variable names (`component.format`, `asset.path`, …) are precomputed keys of each resolver; out: first-present `Optional<Object>`.

### Decisive source
```java
public Optional<Object> get(final String variable) {
  return resolvers.stream()
      .map(vr -> vr.resolve(variable))
      .filter(Optional::isPresent)
      .map(Optional::get)
      .findFirst();                              // FIRST resolver wins
}

// JexlSelector wraps the source as a LAZY, memoized, write-denying JexlContext
new JexlContext() {
  private final Set<String> names = source.getVariableSet();
  private final Map<String, Optional<?>> values = new HashMap<>(names.size());

  public boolean has(final String name) { return names.contains(name); }
  public Object get(final String name) {
    return values.computeIfAbsent(name, source::get).orElse(null);   // resolve once per variable
  }
  public void set(final String name, final Object value) {
    throw new UnsupportedOperationException();                        // context is read-only
  }
}
```

**Flow:** callers build a `VariableSource` via `VariableSourceBuilder.addResolver(...)` — e.g. `PropertiesResolver("asset", map)` exposes `map` keys as `asset.<key>`, `ConstantVariableResolver(value, "X")` answers only `X` → at evaluation JEXL consults `has()` against the precomputed name superset → each referenced variable resolves once (memoized in the context) through the chain, first present wins.
**Invariant:** resolution order is construction order (tested), the name superset is fixed at build time, per-variable work happens at most once per evaluation, and no path exists for expressions to write back into any resolver or the context.
**Probe:** `public/common/components/nexus-selector/src/test/java/org/sonatype/nexus/selector/VariableSourceTest.java` — `test3ResolversFirstWins` (:37–68) proves order precedence across three resolver arrangements; `testNoResolvers` (:71–76) empty source ⇒ absent everywhere. Sandbox write denial pinned by `JexlSelectorTest.testWriteBlocked`. Caveat: the per-evaluation memoization inside `asJexlContext` has no direct test — verified by source reading only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nexus-public", query: "VariableSource VariableResolver PropertiesResolver ConstantVariableResolver first wins", limit: 10 });
```
Live result (2026-08-26): 105 total hits; top rows = `VariableSourceTest.test3ResolversFirstWins`, `ConstantVariableResolver` ctor (:34–37), `VariableSource` ctor (:32–39), `PropertiesResolver` ctor (:45–53), `VariableResolver.resolve/getVariableSet`.

## Verdict
Adopt the resolver-chain + lazy-context pairing: it keeps per-request cost proportional to variables actually referenced and makes "which variables exist" a cheap set-membership question. Adapt namespaces to your domain objects; implement resolvers as thin adapters over your records. Omit `Properties` overload if you have no legacy property files. Caveat: memoization claim rests on source inspection, not a test — keep it if you port, but don't rely on cross-evaluation caching (the context dies with one `evaluate` call).
