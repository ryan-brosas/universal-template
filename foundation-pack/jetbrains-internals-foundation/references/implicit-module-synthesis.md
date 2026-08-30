<!-- capsule-v2 -->
# `$implicit` module synthesis — how does the runtime give ONE code module to SEVERAL plugins without making it globally visible?

**Source:** JetBrains IDE installed build `Rider RD-262.8665.400` (proprietary distribution; study/reference use only); `modules/module-descriptors.jar` top-level descriptor plane, cross-checked pycharm/webstorm. **Question:** Visibility tiers are public/internal/private and `private` hides a module from every other namespace — so how do per-plugin modules (a watcher hook, a copyright bridge, oshi for one daemon) ever depend on a shared jar without promoting it to `public`?

## The `<consumer>_$implicit` namespace
**Path/Symbol:** decisive instance `intellij.fileWatcher.webDeployment_com.intellij.plugins.watcher_$implicit.xml` (whole 13 lines) + second specimen `intellij.less.copyright_org.jetbrains.plugins.less_$implicit.xml`. Filename grammar: `<module-name>_<consumer-namespace>$implicit.xml`; rider ships 20, pycharm 23, webstorm 17.
**Signature:** `<module name="X" namespace="<consumer-plugin-id>_$implicit" visibility="private"> <dependencies>…</dependencies> <resources><resource-root path="../plugins/<owner>/lib/modules/X.jar"/></resources> </module>` — plus the sibling idiom `<lib>_<consumer>_$legacy_jps_library.xml` (rider: 12 such scoped library shims, e.g. three separate `github.oshi.core_*` scopies; and exactly ONE scoped module shim `intellij.platform.commercial.dependencies_com.jetbrains.gateway_$legacy_jps_module.xml`).
**Data Shape:** the namespace IS the grant: reusing the owning plugin's id as namespace prefix makes the private module resolvable inside that plugin's scope only. One physical jar (`resource-root`) can be exposed through MULTIPLE synthetic descriptors — `intellij.platform.commercial.verifier` appears under `_com.intellij.kubernetes`, `_com.intellij.css`, `_com.intellij.database`, `_com.intellij.diagram` (4 of rider's 20).

### Decisive source
```xml
<?xml version="1.0" encoding="UTF-8"?>
<module name="intellij.fileWatcher.webDeployment" namespace="com.intellij.plugins.watcher_$implicit" visibility="private">
  <dependencies>
    <module name="intellij.webDeployment" namespace="$legacy_jps_module"/>
    <module name="intellij.platform.core"/>
    <module name="intellij.fileWatcher" namespace="$legacy_jps_module"/>
    <module name="intellij.platform.util" namespace="$legacy_jps_module"/>
    <module name="intellij.platform.projectModel"/>
  </dependencies>
  <resources>
    <resource-root path="../plugins/fileWatcher/lib/modules/intellij.fileWatcher.webDeployment.jar"/>
  </resources>
</module>
```

**Flow:** build detects that plugin P's code needs module M but M must stay invisible platform-wide → emits M.jar physically under P's (or another plugin's) `lib/modules/` → synthesizes descriptor(s) with namespace `P_$implicit`, visibility `private` → loader resolves M only for classloaders inside P's scope → no global export ever happens.
**Invariant:** scope-by-namespace, not scope-by-path — the resource path locates bytes, but what gates resolution is the namespace matching the consuming plugin's id. Wrong port: "solving" the sharing need by flipping these modules to `public` (breaks encapsulation the tier system exists to keep) or by merging them into the host module (breaks their independent dependency sets). Also: `$implicit` descriptors are TOP-LEVEL files (not under `plugins/`), so a census that walks only `plugins/*.xml` misses them.
**Probe:** anchored at the Rider install root `/mnt/hdd/utopia/inspo/reference/jetbrains/rider`:
```bash
python3 -c "import zipfile;z=zipfile.ZipFile('modules/module-descriptors.jar');hits=[n for n in z.namelist() if n.endswith('_\$implicit.xml')];print(len(hits));print('\n'.join(hits[:5]))"
```
→ `20` followed by five names incl. `intellij.platform.commercial.verifier_com.intellij.kubernetes_$implicit.xml`.
**Retrieve:** (jar-resident manifest plane — not symbol-indexed)
```bash
unzip -p modules/module-descriptors.jar 'intellij.fileWatcher.webDeployment_com.intellij.plugins.watcher_$implicit.xml'
```

## Verdict
Adopt: namespace-scoped synthetic descriptors as the mechanism for per-consumer visibility of a shared implementation jar — the general form is "grant = namespace prefix over a private module," portable to any container with namespaced visibility. Adapt the filename grammar to your serializer. Omit concrete module lists (product content). Extends `module-descriptor-repository` (which owns the substrate and visibility tiers): this capsule owns the SYNTHESIS pattern that keeps those tiers closed while still composing per-plugin functionality.
