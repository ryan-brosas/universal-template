<!-- capsule-v2 -->
# Shell↔Viewer shared dependency closure — should sibling GUI products of one install share one deps.json?

**Source:** JetBrains dotTrace standalone distribution (proprietary distribution; study/reference use only, citations-only), pin `?@?` (not git-managed; identity = root + generation 2026-08-24T13:55:36Z); Codebase Memory `jetbrains-dottrace`. **Question:** When one payload serves two entry exes (home shell + snapshot viewer), where does product differentiation live?

## Byte-identical deps.json twins; identity lives in the apphost, never the dependency graph
**Path/Symbol:** `JetBrains.dotTrace.Home.Shell.deps.json` ≡ `JetBrains.dotTrace.Viewer.deps.json` (both 50,044 bytes, `cmp` IDENTICAL).
**Signature:** `.NETCoreApp,Version=v8.0` targets slot; 99 libraries; 129 `"rid"`-keyed runtimeTargets = 113 `NetCore/*.dll` rid:`any` relocations + 16 `runtimes/<rid>/native` slots (ComponentManager win-x86/x64/arm64, NativeHooks win, libleveldb linux/mac/musl RID set).
**Data Shape:** two thin native apphosts (`JetBrains.dotTrace.Home.Shell.exe`, `JetBrains.dotTrace.Viewer.exe`) over ONE managed payload; the deps.json graph cannot tell which product boots.

### Decisive source
```text
cmp JetBrains.dotTrace.Home.Shell.deps.json JetBrains.dotTrace.Viewer.deps.json → IDENTICAL
grep -c '"rid"' …Viewer.deps.json → 129
ls -la → both files 50044 bytes
```

**Flow:** bootstrapper exe resolves its own `.deps.json` beside it → identical graphs mean both personas load the same assemblies from the same NetCore/ relocation plane and the same native RID ladder → whatever differs (entry Main, Avalonia shell composition, viewer feature modules) is chosen by the managed entry assembly each apphost names — a packaging decision invisible to dependency resolution.
**Invariant:** adding an assembly for one persona changes BOTH unless you split the manifests; conversely you may freely differentiate personas at the apphost/managed-entry layer without touching deps. The two-plane runtimeTargets grammar (relocated managed rid:any vs per-RID native) must be preserved by any layout tool.
**Probe:** deterministic probes executed this pass: byte-compare (IDENTICAL), `"rid"` census 129, size equality 50,044 ×2 — recorded in verification.md.

## Get live surrounding code
**Retrieve:**
```ts
// Graph note: deps.json content is not symbol-indexed in this project; the layout contract
// was located via pass-1 graph work (dotnet-deps-json-layout-map family) and is grounded here
// by direct artifact reads only.
await mcp.codebase_memory.search_graph({ project: "jetbrains-dottrace",
  query: "deps json runtimeTargets NetCore", limit: 5 });
```

## Verdict
Adopt single-closure multi-persona packaging when siblings are truly one product with different entries: it makes "install once, boot as X or Y" free and keeps RID handling in exactly one manifest. Adapt by splitting deps.json only when a persona needs genuinely disjoint dependencies. Omit per-exe dependency drift — with identical closures, any observed behavior difference is an apphost/entry-layer fact.
