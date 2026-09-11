<!-- capsule-v2 -->
# Release-train platform identity — when are two IDEs' platform jars byte-identical?

**Source:** JetBrains IDE distributions (proprietary distribution); study/reference use only. **Question:** How do you tell "shared platform" from "product layer" in a multi-product distribution, and what md5 grouping pattern proves it?

## Connected graph-selected seam
**Path/Symbol:** cross-IDE `lib/*.jar` md5 census (13 installs, 262 train + 261 dataspell/mps).
**Signature:** group by `md5(lib/intellij.xml.psi.impl.jar)` → exactly 2 clusters.
**Data Shape (measured 8/23/26):** pure platform libs cluster by RELEASE TRAIN: `intellij.xml.psi.impl.jar` → {clion,datagrip,goland,phpstorm,phpstorm-light,pycharm,rider,rubymine,rustrover,webstorm} identical, vs {dataspell,mps} identical (261 train). Same for `intellij.spellchecker.jar`. But PRODUCT-COMPILED platform modules differ per IDE: `intellij.platform.ide.impl.jar` has 10 distinct hashes with ONE accidental triple {phpstorm,pycharm,rubymine}; `lib/product-backend.jar` is unique per IDE (10/10 distinct).

### Decisive source
```
md5(intellij.xml.psi.impl.jar):
  c860d1749a… = clion datagrip goland phpstorm phpstorm-light pycharm rider rubymine rustrover webstorm
  3b1f72119e… = dataspell mps                      ← the 2026.1 train
md5(product-backend.jar): all 10 distinct          ← per-product compiled surface
```

**Flow:** build system compiles platform once per train → products recompile only their product-jars → byte equality at a platform jar proves SHARED PLATFORM; divergence at platform.ide.impl shows even platform modules can be product-parameterized (compiled against product code).
**Invariant:** NEVER conclude "shared platform" from one jar's hash — sample a PURE library jar AND a product jar; the pair of results (identical-lib + divergent-product) is the signature. Single-jar claims produce false sharing (the ide.impl triple) or false splits.
**Probe:** rerun: `md5sum */lib/intellij.xml.psi.impl.jar | sort` → 2 lines for 12 files; `md5sum */lib/product-backend.jar | sort -u | wc -l` → equals install count.
**Coverage caveat:** binary-plane method capsule; no graph involvement.

## Get live surrounding code
**Retrieve:**
```ts
// no graph plane — verify via filesystem hashes as above; complements pass-2 catalog-hash parity note
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "platform product module", limit: 3, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-sample discrimination method (pure-lib jar + product jar) for any vendored multi-app distribution. Adapt hash choice to your artifact manager. Omit conclusions about unmeasured jars. Upgrades pass-1's cluster-platform-parity-note from "catalog-hash check" to a measured per-train model with the product-compiled-platform caveat.
