<!-- capsule-v2 -->
# Module-visibility tiers — what does `visibility=` on a module descriptor mean, who enforces it, and is a module's tier stable across products?

**Source:** JetBrains IDE installed builds (proprietary distribution; study/reference use only) — decisive pins PyCharm `PY-262.9437.214`, Rider `RD-262.8665.400`, CLion `CL-262.9437.136`, WebStorm `WS-262.9437.145`; Codebase Memory `jetbrains-pycharm` (109,113n/531,629e, ready; manifest plane is jar-resident, not symbol-indexed). **Question:** Every module descriptor root carries exactly one `visibility="…"` — what is the value vocabulary, where does the runtime enforce it, and can a porter assume tier identity travels with the module name across IDE distributions?

## Root attribute on every module descriptor
**Path/Symbol:** `<ide>/modules/module-descriptors.jar:<module>.xml:2` (root node attribute) — enforcement classes `com/intellij/ide/plugins/ModuleVisibility`, `com/intellij/ide/plugins/PluginModuleVisibilityCheckOption` (host: `lib/intellij.platform.core.impl.jar`), parser enum `com/intellij/platform/pluginSystem/parser/impl/elements/ModuleVisibilityValue`.
**Signature:** `<module name="…" namespace="…" visibility="public|internal|private">` — the ONLY attributes ever seen on a root node cluster-wide are `name` (always), `namespace` (on typed nodes), `visibility` (exactly once per file, no default).
**Data Shape:** Closed three-value vocabulary confirmed twice: corpus sweep (only these three values occur across 14k+ descriptors in 10 v2-format products) AND constant pools of BOTH enums (`PUBLIC INTERNAL PRIVATE` in `ModuleVisibility` and parser-side `ModuleVisibilityValue`). Dependency `<module>` nodes carry ONLY `name`+`namespace` — no loading/visibility marker exists on this plane (that vocabulary lives in the plugin-descriptor layer, owned by `plugin-descriptor-loading-matrix`).

### Decisive source
```xml
<!-- rider/modules/module-descriptors.jar:intellij.xml.syntax.xml:2 -->
<module name="intellij.xml.syntax" namespace="jetbrains" visibility="private">
<!-- same module, clion/pycharm/webstorm :2 -->
<module name="intellij.xml.syntax" namespace="jetbrains" visibility="internal">
```

```text
$ unzip -p lib/intellij.platform.core.impl.jar com/intellij/ide/plugins/PluginModuleVisibilityCheckOption.class | strings | grep -E '^(DISABLED|REPORT_WARNING|REPORT_ERROR)$'
DISABLED
REPORT_WARNING
REPORT_ERROR
```

**Flow:** build stamps one tier per module → serialized to `module-descriptors.dat` + mirrored as XML jar → boot parses through `ModuleVisibilityValue` → `PluginSetBuilder.kt` runs the visibility check with per-install severity (`DISABLED` / `REPORT_WARNING` / `REPORT_ERROR`) — i.e. violations are configurable diagnostics, not hard loader failures.
**Invariant:** (1) Tiers are NOT a security lattice: resolved dependency edges exist from EVERY tier to EVERY tier — pycharm public→private 184, private→private 206, internal→private 61 (rider 173/190/54; same shape in webstorm/clion). Never port this as an access-control DAG; it is packaging metadata. (2) Tier identity travels with the module NAME: 1,072 bare-name modules ship in ALL of the 10 v2-format products and 1,070 (99.8%) carry the IDENTICAL tier in every one; pycharm∩webstorm common set 1,357 with ZERO disagreement. Exactly TWO conflicts exist cluster-wide, both rider-only downgrades: `intellij.platform.ide.impl.wsl` public→internal and `intellij.xml.syntax` internal→private (confounder: rider sits on micro-line 262.8665 vs 9437 elsewhere). (3) Corollaries: every `<X>_<consumer>_$implicit` synthetic descriptor is private (pycharm 23/23); every `$legacy_jps_library` shim is public (117/117); DataSpell DS-261 (old flat format generation) carries ZERO visibility attrs — presence of the attr is itself a format-generation marker. (4) Cluster census (occurrences): pycharm 654/420/528 · rider 683/409/526 · clion 681/442/551 · phpstorm 642/354/519 · webstorm 619/352/486 · rubymine 620/355/487 · rustrover 617/362/493 · goland 586/359/503 · phpstorm-light 580/349/467 · datagrip 493/312/341 (public/internal/private). **ERRATUM vs [DONE:340]:** that entry recorded pycharm public=301; machine recount (two independent methods: grep over the extracted tree AND a zipfile probe) returns **654**, while its rider 683/409/526 and pycharm internal/private 420/528 reproduce EXACTLY here — trust this table.
**Probe:** anchored at the PyCharm install root `$REFERENCE_ROOT/reference/jetbrains/pycharm`:
```bash
python3 -c "import zipfile,re,collections; z=zipfile.ZipFile('modules/module-descriptors.jar'); c=collections.Counter(); [c.update(re.findall(r'visibility=\"(\w+)\"', z.read(n).decode('utf-8','replace'))) for n in z.namelist() if n.endswith('.xml')]; print(dict(c))"
```
→ `{'public': 654, 'internal': 420, 'private': 528}`

## Get live surrounding code
**Retrieve:** (jar-resident manifest plane — not symbol-indexed; the graph's code plane holds helpers/scripts only)
```bash
cd $REFERENCE_ROOT/reference/jetbrains && for p in rider clion pycharm webstorm; do echo "$p: $(unzip -p $p/modules/module-descriptors.jar intellij.xml.syntax.xml | sed -n '2p' | grep -o 'visibility="[a-z]*"')"; done
```
Adversarial wrong-project check executed pre-write: `search_graph {"project":"jetbrains-datagrip","query":"ModuleVisibility visibility tiers","limit":3}` → `total: 0`.

## Verdict
Adopt: a closed-vocabulary, once-per-descriptor tier attribute whose values are stable for a given module name across all distributions of the same release train, with `$implicit`=private / jps-library-shim=public corollaries and old-format detection by attr absence. Adapt: the tier vocabulary names and the diagnostic-severity ladder to your container. Omit: treating tiers as an access lattice (dependency edges contradict it), and the enforcement internals beyond the two enum + check-option seams (implementation source not shipped in these builds). Pairs with `module-descriptor-repository` (substrate), `implicit-module-synthesis` (private-synthesis rule), `plugin-descriptor-loading-matrix` (the OTHER per-module attribute, `loading=`, on a different node layer).
