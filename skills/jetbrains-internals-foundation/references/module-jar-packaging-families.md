<!-- capsule-v2 -->
# Module-jar packaging families — where do a module's bytes actually live, and how do you map descriptor → jar?

**Source:** JetBrains IDE installed builds (proprietary distribution; study/reference use only) — census over the 9 v2-format products at pins PY-262.9437.214 / WS-262.9437.145 / RD-262.8665.400 / CL-262.9437.136 / GO-262.9437.195 / PS-262.9437.196 / RM-262.9437.192 / RR-262.9437.161 / DB-262.9437.163; Codebase Memory `jetbrains-pycharm` (manifest plane jar-resident, not symbol-indexed). **Question:** Each module descriptor names a `resource-root` jar — what is the full grammar of those paths, which jars host many modules, and can a porter assume the XML mirror lists every runtime module?

## Resource-root path families
**Path/Symbol:** `<ide>/modules/module-descriptors.jar:<module>.xml` → `<resources><resource-root path="…"/></resources>` (1,646 refs over pycharm's 1,602 descriptors; 1,349 distinct paths). Container elements per descriptor: exactly `<dependencies>` and/or `<resources>` — nothing else (cluster tag census).
**Signature:** Four families, all relative to the owning descriptor's natural location: `../lib/<name>.jar` (platform layer, FLAT — zero top-level `lib/modules/` dirs exist in ANY product), `../plugins/<plugin>/lib/modules/<module>.jar` (plugin layer, one-jar-per-module convention), `../plugins/<plugin>/lib/<name>.jar` (shared plugin jars), plus a rare fifth shape (`lib/ext/platform-main.jar`, `lib/frontend-split/*.jar`, `gateway-standalone/*.jar` — 8 distinct paths in pycharm, same order elsewhere).
**Data Shape:** The `lib/modules/` sub-directory convention belongs to the PLUGIN layer only: pycharm 726 of 1,646 resource-roots point into `plugins/*/lib/modules/`, clion 781/1,708, rider 643/1,684, webstorm 579/1,499 (~40% cluster-wide); platform modules ride flat lib jars.

### Decisive source
```xml
<!-- pycharm .../intellij.platform.lang.xml (public platform module -> flat lib jar) -->
<resources>
    <resource-root path="../lib/intellij.platform.lang.jar"/>
</resources>
```

```xml
<!-- pycharm .../intellij.grazie.markdown.xml (plugin-layer module -> lib/modules convention) -->
<resources>
    <resource-root path="../plugins/grazie/lib/modules/intellij.grazie.markdown.jar"/>
</resources>
```

**Flow:** descriptor name → its single `<resource-root>` → physical jar (relative to `modules/`, i.e. install-root-relative after stripping `../`) → classloader wires the jar into that module's loader.
**Invariant:** (1) ONE JAR HOSTS MANY MODULES regularly — the mapping is N:1: pycharm's top hosts are `plugins/fullLine/lib/fullLine.jar` (62 module descriptors!), `lib/intellij.platform.ide.impl.jar` (22), `lib/util-8.jar` (17); every product has 3–5 such ≥10-module jars. A porter who assumes jar==module breaks here. (2) THE MIRROR IS PARTIAL: bare-name dependencies with NO descriptor in this jar resolve inside the binary truth instead — e.g. `intellij.cidr.core`, cited by ~280 pycharm dep refs, is ABSENT from the XML mirror but byte-findable in `module-descriptors.dat`. Cross-product references (CLion-only modules cited by descriptors shipped in every IDE) are the bulk of these. Diffing or porting from the XML mirror alone undercounts the runtime graph; treat `.dat` as superset, mirror as the readable projection.
**Probe:** anchored at the PyCharm install root `$REFERENCE_ROOT/reference/jetbrains/pycharm`:
```bash
python3 -c "import zipfile,re,collections; z=zipfile.ZipFile('modules/module-descriptors.jar'); c=collections.Counter(); [c.update(re.findall(r'<resource-root path=\"([^\"]+)\"', z.read(n).decode('utf-8','replace'))) for n in z.namelist() if n.endswith('.xml')]; print(len(c), sum(v for k,v in c.items() if '/lib/modules/' in k))"
```
→ `1349 726`
and the mirror-gap probe:
```bash
python3 -c "data=open('modules/module-descriptors.dat','rb').read(); print('FOUND' if data.find(b'intellij.cidr.core')>=0 else 'ABSENT')"
```
→ `FOUND`

## Get live surrounding code
**Retrieve:** (jar-resident manifest plane — not symbol-indexed)
```bash
cd $REFERENCE_ROOT/reference/jetbrains/pycharm && unzip -p modules/module-descriptors.jar intellij.grazie.markdown.xml && unzip -l plugins/fullLine/lib/fullLine.jar | head -5
```

## Verdict
Adopt: the four-family path grammar and the plugin-layer `lib/modules/` one-jar-per-module convention as the packaging contract; adopt N:1 jar hosting as an expected case (dedupe by resolved path). Adapt: directory layout to your container while keeping the platform-flat vs plugin-modular split. Omit: assuming the XML mirror is complete (the `.dat` carries modules the mirror lacks) and any Velocity/build-pipeline reasoning about WHY a module landed in a shared jar. Pairs with `module-descriptor-repository` (substrate + .dat truth), `module-descriptor-split-grammar` (descriptor interior), `implicit-module-synthesis` (shared private jars via namespace synthesis).
