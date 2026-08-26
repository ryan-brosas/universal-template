<!-- capsule-v2 -->
# JEXL sandbox engine — how do you let users write expressions that run inside your server without handing them an RCE?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d`; Codebase Memory `nexus-public`. **Question:** How do you host user-authored expression evaluation so constructors, property writes, and arbitrary method calls are structurally impossible while reads and comparisons still work?

## Hardened engine + receiver-typed uberspect whitelist
**Path/Symbol:** `public/common/components/nexus-selector/src/main/java/org/sonatype/nexus/selector/JexlEngine.java:JexlEngine,parseExpression,buildExpression,expandExceptionDetail` (:38–105); `internal/SandboxJexlUberspect.java:getConstructor,getMethod,getPropertySet` (:33–80).
**Signature:** `class JexlEngine extends Engine { JexlEngine(); ASTJexlScript parseExpression(String); JexlExpression buildExpression(String, boolean shouldTrimLeadingSlash); static String expandExceptionDetail(JexlException); }`; `class SandboxJexlUberspect extends Uberspect`.
**Data Shape:** in: raw expression string; out: parsed `ASTJexlScript` / wrapped `JexlExpression`; parse failures throw `JexlException` subclasses carrying `JexlInfo` (line/column/detail).

### Decisive source
```java
public JexlEngine() {
  super(new JexlBuilder().uberspect(new SandboxJexlUberspect()));   // sandbox is THE only guard layer
}

public ASTJexlScript parseExpression(final String expression) {
  String source = trimSource(checkNotNull(expression));
  return parse(CALLER_INFO, source, null, false, true);
}

// SandboxJexlUberspect: deny everything except a per-receiver-type method whitelist
private static final Set<String> COLLECTION_METHODS = ImmutableSet.of("contains");
private static final Set<String> MAP_METHODS = ImmutableSet.of("get", "getOrDefault", "containsKey", "containsValue");
private static final Set<String> STRING_METHODS = ImmutableSet.of("toUpperCase", "toLowerCase", "endsWith", "startsWith");

public JexlMethod getConstructor(final Object ctorHandle, final Object... args) {
  return null;                                    // new(...) always unresolvable
}
public JexlMethod getMethod(final Object obj, final String method, final Object... args) {
  if (obj instanceof String && STRING_METHODS.contains(method)) return super.getMethod(obj, method, args);
  else if (obj instanceof Map && MAP_METHODS.contains(method)) return super.getMethod(obj, method, args);
  else if (obj instanceof Collection && COLLECTION_METHODS.contains(method)) return super.getMethod(obj, method, args);
  return null;
}
public JexlPropertySet getPropertySet(final Object obj, final Object identifier, final Object arg) {
  return null;                                    // all writes unresolvable
}

// this stops JEXL from using expensive new Throwable().getStackTrace() to find caller info
private static final JexlInfo CALLER_INFO = new JexlInfo("Selector", 0, 0);
```

**Flow:** engine constructed once per factory with sandboxed uberspect → `parseExpression` trims input and parses under a fixed synthetic `CALLER_INFO` → sandbox resolves identifiers via the JEXL context but denies constructors/writes and non-whitelisted methods by returning null (unresolvable ⇒ evaluate-time `JexlException`) → failures are humanized by `expandExceptionDetail`, which strips JEXL's condensed `Selector@n:l!…` header and appends `in '<detail>' at line L column C`.
**Invariant:** returning null (not throwing) from the uberspect is what makes denial structural — there is no code path from expression text to constructor invocation, mutation, or reflection; whitelists are keyed on receiver *type*, not name, so `map.put(...)` is denied even though `getOrDefault` is allowed.
**Probe:** `public/common/components/nexus-selector/src/test/java/org/sonatype/nexus/selector/JexlSelectorTest.java` — `testNoConstructor` (:158–163) `new('...JexlSelector...', ...)` ⇒ JexlException; `testMethodsBlocked` (:165–170) `writeableMap.put(...)` ⇒ JexlException; `testWriteBlocked` (:172–177) `writeableObj.foo = 'xxx'` ⇒ JexlException; `testStringToUppercase` (:145–149) and pretty-exception trio (:64–107) pin the allowed side and exact `"parsing error in '&&' at line 1 column 1"` detail format.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nexus-public", query: "SandboxJexlUberspect JexlEngine sandbox uberspect blocked constructor", limit: 10 });
```
Live result (2026-08-26): 92 total hits, top rows = `SandboxJexlUberspect` class + ctor/getConstructor/getMethod/getPropertySet (:33–80) and `JexlEngine` ctor/parse/build (:38–105).

## Verdict
Adopt the deny-by-default uberspect (null-returning overrides + tiny per-receiver-type method whitelist), the fixed synthetic caller-info to skip stack-walk cost, and the exception-detail humanizer for user-facing validation messages. Adapt the whitelist contents to your own variable namespaces. Omit the `shouldTrimLeadingSlash` hook unless you also port the leading-slash normalizers (see `leading-slash-path-normalization`) — production wiring currently passes `false`. Caveat: commons-jexl3 internals (`Uberspect` superclass) are version-coupled; re-run the three block tests after any JEXL upgrade.
