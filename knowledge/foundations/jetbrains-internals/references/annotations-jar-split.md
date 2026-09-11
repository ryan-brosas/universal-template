<!-- capsule-v2 -->
# Annotations jar split — why does org.jetbrains.annotations ship twice with different halves?

**Source:** JetBrains IDE distributions (proprietary distribution; study/reference use only); direct jar reads; Codebase Memory `jetbrains-pycharm`. **Question:** Which nullability/concurrency contract annotations exist, where do they physically live at runtime, and what does that split tell a porter about compile-time vs runtime contracts?

## Two-jar annotation split
**Path/Symbol:** `lib/annotations.jar!org/jetbrains/annotations/*` (99 classes) vs `lib/intellij.platform.core.jar!org/jetbrains/annotations/*` (9 classes: `CalledInAny`, `SystemDependent`, `SystemIndependent` + Nls family members).
**Signature:** `@NotNull`, `@Nullable`, `@Unmodifiable`, `@Contract("... -> ...")` (annotations.jar — broad contract set); `@CalledInAny`, `@SystemDependent`, `@SystemIndependent` (platform.core — threading + path-semantics annotations needed BY platform code itself).
**Data Shape:** cluster census 452 annotation-class occurrences across 12 products; every product repeats the SAME split (rider 45 incl. its extra modules). The platform core carries ONLY the annotations its own signatures reference; the fat jar carries the rest for compiled-in dependencies of other code.

### Decisive source
```
lib/annotations.jar
  org/jetbrains/annotations/{NotNull, Nullable, Contract, Unmodifiable, ...}   (99 classes)
lib/intellij.platform.core.jar
  org/jetbrains/annotations/{CalledInAny, SystemDependent, SystemIndependent} (9 classes)
```

**Flow:** platform API methods are annotated `@SystemIndependent` etc. → those annotation classes must be ON the compile AND runtime classpath of every module → they ride inside platform.core itself (no extra dependency edge) → tooling-only annotations (`@Contract` evaluation, nullability external checks) stay in annotations.jar which only analysis needs.
**Invariant:** the split is a dependency-cycle breaker: an annotation must never force a jar to depend on another jar just for a marker interface. Wrong port: merging all annotations into one library jar and making platform.core depend on it (creates a cycle or a heavier classpath).
**Probe:** `unzip -l pycharm/lib/intellij.platform.core.jar | grep -c 'org/jetbrains/annotations'` → 9; `unzip -l pycharm/lib/annotations.jar | grep -c 'org/jetbrains/annotations'` → ~99.
**Coverage caveat:** resource-plane capsule; cited via direct jar extraction.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "NotNull contract annotation nullability", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: keep contract-annotation classes co-located with the module whose SIGNATURES use them; treat richer annotation sets as optional analysis-time deps. Adapt package layout to your host. Omit JetBrains' specific annotation inventory. Pass-4 adjudication of the census's `annotations_jar` probe: real pattern, now captured.
