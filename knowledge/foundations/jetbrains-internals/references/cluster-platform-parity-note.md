<!-- capsule-v2 -->
# Cluster platform parity note — shared platform catalog identity across IDEs

**Source:** JetBrains IDE installed builds, 2026.2 train; Codebase Memory `jetbrains-*` projects. **Question:** How do you verify which manifest layers are SHARED versus product-specific across a fleet of installed IDEs?

## Parity check
**Path/Symbol:** `lib/intellij.platform.ide.impl.jar:META-INF/PlatformExtensionPoints.xml` in each of pycharm/webstorm/rider/clion/goland/rustrover/rubymine/phpstorm/phpstorm-light/datagrip (md5 `fdcd5edd` for ALL ten).
**Signature:** `unzip -p <ide>/lib/intellij.platform.ide.impl.jar META-INF/PlatformExtensionPoints.xml | md5sum`.
**Data Shape:** identical bytes ⇒ the platform EP vocabulary is one contract per release train; product differentiation lives ONLY in product fragments and plugin descriptors. Divergences found: DataSpell `cf54096d` (older 261 train), MPS `d41d8cd9` (empty — MPS is not IntelliJ-lang based), air/dotmemory/dottrace lack the platform jar entirely.

### Decisive source
```text
pycharm fdcd5edd   webstorm fdcd5edd   rider fdcd5edd
clion   fdcd5edd   goland   fdcd5edd   rustrover fdcd5edd
rubymine fdcd5edd  phpstorm fdcd5edd  datagrip   fdcd5edd
dataspell cf54096d (261 train)        mps d41d8cd9 (no platform EPs)
air / dotmemory / dottrace: NO intellij.platform.ide.impl.jar
```

**Flow:** hash a known catalog file per install → equal hashes = shared platform layer → only then compare product/plugin layers for real differences.
**Invariant:** never diff whole distributions to learn what products share — diff the PLATFORM CATALOG identity first; everything above it is layered customization. Wrong port: treating each IDE's manifests as independent dialects and re-deriving shared contracts N times.
**Probe:** deterministic: run the md5 loop above over all 15 installs; expect exactly the split shown (10×fdcd5edd + dataspell + mps + 3 no-platform).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "platform extension points", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt catalog-hash parity checking when mining any multi-product distribution family; adapt to your artifact format; omit nothing portable here. Coverage caveat: hashes pinned 2026-08-23 at the build numbers in leaf Provenance.
