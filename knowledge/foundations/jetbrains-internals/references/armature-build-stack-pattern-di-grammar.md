<!-- capsule-v2 -->
# Armature build-stack-pattern DI grammar — how does a profiler compose its object graph when the container's whole contract ships as XML doc comments?

**Source:** JetBrains dotTrace standalone distribution (proprietary distribution; study/reference use only, citations-only), pin `?@?` (not git-managed; identity = root + Codebase Memory generation 2026-08-24T13:55:36Z); Codebase Memory `jetbrains-dottrace`. **Question:** What registration/resolution design does BeatyBit.Armature (the third-party DI container JetBrains ships inside dotTrace) actually use, and what does its presence tell you about packaging this repo?

## Pattern tree + weights + staged pipeline, not a service map
**Path/Symbol:** root `Armature.xml` :2-1223 (`BeatyBit.Armature`, full fluent surface), `Armature.Core.xml` :2-672 (`Builder`, `BuildSession`, `BuildSession.Stack`, pattern-tree core), `Armature.Interface.xml` :2-21 (the whole "interface" assembly = `InjectAttribute` + optional `Tag` field).
**Signature:** `Builder.#ctor(String name, Object[] buildStages, IBuilder[] parentBuilders)` couples a `BuildStackPatternTree`, an ordered stage list, and parent-container fallback into one resolver (`Armature.Core.xml:169-181`). Registration is a tuner chain: `Treat/TreatOpenGeneric/TreatInheritorsOf/TreatAll(type, tag)` → `Building<T>(context)` → `AsIs/AsInstance/As/CreatedByReflection/AsCreatedWith(...)` → `UsingArguments(...)`/`UsingInjectionPoints(ForParameter|ForProperty|Constructor|Property...)` → `AsSingleton` (`Armature.xml:1030-1069, 890-1001, 762-838`).
**Data Shape:** every match is a weighted unit pattern (`IsParameterOfType`, `IsPropertyNamed`, `IsGenericOfDefinition`, `CanBeInstantiated`, …) on a build stack; resolution context is the whole dependency stack `IA -> A -> IB -> B -> int` (`BuildSession.Stack`, Core:249-254), so rules can key on *where* a type is being built, not just what it is.

### Decisive source
```text
Armature.xml:563-574 (WeightOf.UnitPattern summary):
  "Weights of UnitPattern is about two orders of magnitude higher than weights of
   InjectionPoint in order to registrations like [subtype-of-string rule] never 'wins'
   [exact-type registration] because the second one is narrower case than the first one"
Armature.xml:375-387 (BuildStage): stages are plain objects, NOT enum/int
  ("Use objects but int or enum in order to avoid memory traffic on boxing");
  pipeline example Builder(Intercept, Cache, Initialize, Create) — Create runs first
  (ctor injection), then Initialize (property/method injection via PostProcess),
  then Intercept (subscribe/log), then Cache.
Armature.xml:247-261 (TryInOrderBase): composite fallback action, IEnumerable-initializable:
  new TryInOrder { new GetConstructorByInjectPoint(), new GetConstructorWithMaxParametersCount() }
Armature.xml:287-289: runtime Build() arguments are temporary session registrations whose
  "weight is decreased" — permanent registrations take precedence over call-site args.
```

**Flow:** `Build<T>` → session walks the pattern tree matching the current build stack → matched actions run stage-by-stage (`Process` creates in the Create stage; `PostProcess` injects/intercepts/caches downstream) → unbuilt units fall through to `parentBuilders` in constructor order (container hierarchy) → `TryInOrder` gives within-stage fallback ladders.
**Invariant:** specificity resolution is NUMERIC, not textual — unit-pattern weights sit ~two orders of magnitude above injection-point weights so a narrower exact-type registration always beats a broad subtype rule without any ordering tricks; caching happens in a later stage than creation/interception, so a cached instance is always fully initialized; `null` is a legal `BuildResult.Value`.
**Probe:** executed this pass — (a) layout: `BeatyBit.Armature{,.Core,.Interface}.dll` ship in BOTH roots (main dll 106,496 B in root and NetCore/ = dual-TFM twin per `dual-tfm-assembly-duplication`) plus `JetBrains.Common.ArmatureExtension.dll` (21,400 B, root only) — the container is live dependency, not dead weight; (b) integrity probe: `NetCore/Armature.xml` is exactly 45,056 bytes (= 44 × 4096, an exact block multiple) vs root's 76,597, and ends mid-tag inside `T:BeatyBit.Armature.ForProperty` — the shipped NetCore doc plane is PHYSICALLY TRUNCATED at a copy-block boundary (od tail shows unterminated `<member …>`). This is the file behind the graph's parse_partial flag (:1-700); no hidden contract exists in the flagged range — the twin is simply cut off. Cite the ROOT plane as authoritative at this pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-dottrace",
  query: "Armature building dependency injection", limit: 50 });
// → jetbrains-dottrace.Armature.doc @ Armature.xml :2-1223 (fully indexed),
//   NetCore/Armature.xml nodes :380-387 etc., Armature.Core.doc @ Armature.Core.xml :2-672,
//   Armature.Interface.doc @ Armature.Interface.xml :2-21 — verified live;
//   member-level text comes from the direct reads above.
// check_index_coverage: root+Core+Interface = no_recorded_issue;
//   NetCore/Armature.xml = partial (parse_partial 1-700) — resolved by direct read.
```

## Verdict
Adopt the shape if you need a profiler-grade embedded container: pattern-tree registrations keyed on build-stack context, numeric weight arithmetic for specificity, object-valued staged pipeline (create→initialize→intercept→cache), parent-builder fallback instead of child containers. Adapt the tuner vocabulary to your domain; keep InjectAttribute+Tag minimal like `Armature.Interface`. Omit boxing-sensitive stage objects unless you resolve millions of units. Packaging caveat to carry forward: shipped XML doc planes can be silently truncated at block boundaries — treat index coverage flags as a truncation detector, and never cite the truncated twin as a second source.
