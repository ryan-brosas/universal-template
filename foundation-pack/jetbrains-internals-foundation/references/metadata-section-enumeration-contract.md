<!-- capsule-v2 -->
# Metadata section enumeration contract — how do you enumerate tens of thousands of metadata entries without materializing what search never needs?

**Source:** JetBrains dotMemory standalone distribution (proprietary distribution; study/reference use only, citations-only), pin `?@?` (not git-managed; identity = install self-hash `41e6f647…` + Codebase Memory generation 2026-08-24T13:53:49Z); Codebase Memory `jetbrains-dotmemory` (5,124 nodes / 5,117 edges, FULL). **Question:** When a stored section holds ~10⁴–10⁵ records whose payload fields only matter for a minority of consumers, which split keeps enumeration fast — and what lifetime rules keep a borrowed provider safe?

## Light/full split over one section interface
**Path/Symbol:** `JetBrains.Profiler.Snapshot.Interface.xml`: `Section.Metadata.Helpers.MetadataSectionHelpers.GetFunctionItemsLight(IMetadataSectionAssemblyProvider, MetadataId)` (:97-106); `Section.Metadata.IMetadataSection.ExecuteWithMetadataAssemblyProvider<TRes,TParam>(Func<TParam,IMetadataSectionAssemblyProvider,TRes>, TParam)` (:108-122); lifetime alternative `GetMetadataAssemblyProvider(Lifetime, Boolean, Boolean)`.
**Signature:** `GetFunctionItemsLight(provider, id)` → FunctionResult with Parameters/ReturnValue NULLed; `ExecuteWithMetadataAssemblyProvider<TRes,TParam>(action, param) → TRes`.
**Data Shape:** one metadata section serves two read profiles: "light" rows for search/tab building vs full rows for signature comparison and tree-node rendering; the provider object is a scoped resource created per delegate invocation unless bound to an explicit Lifetime.

### Decisive source
```xml
<member name="M:...MetadataSectionHelpers.GetFunctionItemsLight(...)">
  Same as GetFunctionItems, but does not fill Parameters and ReturnValue fields
  in the FunctionResult structure. This NULLed values are then requested separately
  with the help of the method GetFunctionParams. This help to significantly reduce
  total time for enumerating all functions (usually tens of thousands in average
  snapshots), because return values and parameters do not participate neither
  in function search nor in tabs creation, only in signature comparisons and in
  visual representation of tree nodes (which # is tens or hundreds).
<member name="M:...IMetadataSection.ExecuteWithMetadataAssemblyProvider``2(...)">
  Note: the instance of IMetadataSectionAssemblyProvider will be disposed when you
  leave this method. So you cannot store it in your action. Also, you cannot use
  yield return statement in action for the same reason.
  If you need to store ... use GetMetadataAssemblyProvider(JetBrains.Lifetimes.Lifetime,...)
```

**Flow:** enumerate functions via the Light variant (rows arrive without param/return payloads) → the few nodes actually rendered or signature-compared request their params separately through `GetFunctionParams` → scoped consumers wrap access in `ExecuteWithMetadataAssemblyProvider` (provider dies at method exit; deferred enumeration inside is forbidden because disposal beats laziness) → long-lived consumers instead obtain a Lifetime-bound provider and own its disposal window.
**Invariant:** the expensive fields are fetched per-CONSUMER-need, never per-row; a scoped provider must never escape its scope (no storing, no `yield return`) — violating either turns O(displayed) work into O(total functions).
**Probe:** deterministic content assertions executed on `/mnt/hdd/utopia/inspo/dotmemory/JetBrains.Profiler.Snapshot.Interface.xml`: line 99 opens the Light summary ("Same as GetFunctionItems, but does not fill Parameters"), lines 113-116 carry the no-store/no-yield note; both verified by direct read of :97-122 this pass.

## Get live surrounding code
**Retrieve:** executed live this pass:
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-dotmemory",
  query: "SectionOffset WriteableSection snapshot storage", limit: 30 });
// → JetBrains.Profiler.Snapshot.doc @ JetBrains.Profiler.Snapshot.Interface.xml :2-135
//   (file-granular index; member text read directly from the cited ranges).
```

## Verdict
Adopt the light/full row split keyed by "does search need this field?" plus the scoped-provider pattern with its explicit no-store/no-yield rule. Adapt field taxonomy to your domain. Omit the profiler-specific FunctionResult shape. Coverage caveat: XML doc plane only — member bodies are compiled; claims rest on shipped API documentation, checked `no_recorded_issue` by check_index_coverage.
