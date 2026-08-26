<!-- capsule-v2 -->
# JetMetadata .sstg precomputed catalog plane — how does a component-platform product start fast outside the IDE?

**Source:** JetBrains dotTrace standalone distribution (proprietary distribution; study/reference use only, citations-only), pin `?@?` (not git-managed; identity = root + generation 2026-08-24T13:55:36Z); Codebase Memory `jetbrains-dottrace` (12,537 nodes, FULL mode). **Question:** Where do precomputed component/part catalogs live in a .NET-hosted JetBrains product, and what shape keeps them deterministic and per-module-set?

## Zip-of-catalog-slots sidecars
**Path/Symbol:** 74 × `*.JetMetadata.sstg` at install root; naming = owning logical module set, e.g. `JetBrains.Platform.Core.Shell.JetMetadata.sstg`, `JetBrains.Profilers.Profiler.Kernel.Core.JetMetadata.sstg`, plus per-RID variants (`JetBrains.dotCommon.Native.Core.linux-x64.Release.JetMetadata.sstg`).
**Signature:** container = ZIP (bytes `50 4b 03 04`, "PK" local-file header); entries are path-like slot keys ending in `/`.
**Data Shape:** observed slots: `PrecalculatedPartCatalog/CatalogTables/`, `JetSubplatformZoningSpecArtifact/`, `RuntimeSpecificPackageReferenceMetadata-01..N/`, `ApplicationPackageArtifact/`, `EulaFileArtifact/{Content,TargetPath}/`, `PackageOriginalProjects/`.

### Decisive source
```text
$ unzip -l JetBrains.Platform.Core.Shell.JetMetadata.sstg | head
  ApplicationPackageArtifact/            0  1980-01-01
  PrecalculatedPartCatalog/CatalogTables/
  RuntimeSpecificPackageReferenceMetadata-01/
$ od -A d -t x1z -N 16 …sstg
50 4b 03 04 14 00 00 00 00 00 ... ("PK..")
```

**Flow:** build time computes each module-set's part catalog/zoning/package-reference metadata once → ships as one ZIP sidecar named after the module set → startup loads catalogs directly from sstg instead of reflecting over assemblies → RID-specific native sets get their own sstg.
**Invariant:** sidecar identity == module-set identity (one sstg per set, never shared); zeroed 1980 timestamps make caches byte-reproducible; slots are path-keyed so new metadata generations (`-01..-N`) append without renaming old ones. This is the .NET-side twin of the IDE platform's precomputed part-catalog idea already captured for JVM builds.
**Probe:** deterministic: PK-magic od dump; `find . -name '*.sstg' | wc -l` → 74; `unzip -l` timestamp column uniformly 1980-01-01.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.check_index_coverage({ project: "jetbrains-dottrace",
  paths: ["JetBrains.Platform.Core.Shell.JetMetadata.sstg"] }); // stored ignored-suffix record
```
Coverage caveat: binary containers are not symbol-indexed; decisive evidence is direct extraction.

## Verdict
Adopt per-module-set precomputed catalog sidecars with path-keyed slots and frozen timestamps for any plugin-platform host needing fast cold start. Adapt slot vocabulary to your component model. Omit the proprietary catalog table formats.