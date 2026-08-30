<!-- capsule-v2 -->
# Plugin-descriptor loading matrix — how does one bundled plugin split its code into modules with three load levels, and what does that layer look like across products?

**Source:** JetBrains IDE installed build `Rider RD-262.8665.400` (proprietary distribution; study/reference use only); manifest plane of `modules/module-descriptors.jar`, cross-product census over 11 installs. **Question:** A plugin.xml used to be one flat extension surface — how does the v2 runtime-repository generation express per-module load gating INSIDE a plugin descriptor, and how big is each level per product?

## The plugins/ descriptor layer
**Path/Symbol:** `<ide>/modules/module-descriptors.jar:plugins/<module>.xml` — decisive instance `plugins/intellij.angular.plugin.xml` (11 lines, whole-file read). These 141 files are the readable mirror of `module-descriptors.dat` (runtime truth; header comment states it verbatim). Complements `module-set-load-levels` (which owns the `intellij.moduleSets.*` plane inside lib jars): THIS capsule owns the per-plugin descriptor layer.
**Signature:** `<plugin id="<plugin-id>">` root carrying `<plugin-descriptor-module name="..." namespace="$legacy_jps_module"/>` plus one `<module name="..." namespace="jetbrains" loading="embedded|optional|required"/>` per code module.
**Data Shape:** `loading` appears ONLY on module nodes inside plugin descriptors — plain top-level module XMLs never carry it. Three levels: `embedded` (rides the host classloader, no separate gate), `optional` (resolved lazily on first dependency resolution), `required` (eager).

### Decisive source
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!-- The IDE doesn't use this file; it takes data from module-descriptors.dat instead -->
<plugin id="AngularJS">
  <plugin-descriptor-module name="intellij.angular.plugin" namespace="$legacy_jps_module"/>
  <module name="intellij.angular.backend" namespace="jetbrains" loading="optional"/>
  <module name="intellij.angular.free" namespace="jetbrains" loading="required"/>
  <module name="intellij.angular.tslint" namespace="jetbrains" loading="optional"/>
  <module name="intellij.angular.plugin" namespace="$legacy_jps_module" loading="embedded"/>
</plugin>
```

**Flow:** build emits one descriptor per plugin → `.dat` serialization → boot loads `required` eagerly, wires `embedded` into the host module's loader, defers `optional` until something resolves against it → the XML mirror exists for humans/diffing only.
**Invariant:** the SAME attribute lives at two layers with different owners — plugin-descriptor layer (this capsule, `loading=` on `<module>` under `<plugin>`) vs module-set layer (`loading=` on `<module>` under `<content>` in lib jars, owned by module-set-load-levels). A porter who copies the wrong specimen gets a schema the loader rejects. Also: the mirror comment ("IDE doesn't use this file") applies to EVERY file in this jar — never diff the mirror and assume runtime changed.
**Probe:** anchored at the Rider install root `/mnt/hdd/utopia/inspo/reference/jetbrains/rider`:
```bash
python3 -c "import zipfile;z=zipfile.ZipFile('modules/module-descriptors.jar');xs=[n for n in z.namelist() if n.startswith('plugins/') and n.endswith('.xml')];t=''.join(z.read(n).decode() for n in xs);print(len(xs), t.count('loading=\"embedded\"'), t.count('loading=\"optional\"'), t.count('loading=\"required\"'))"
```
→ `141 1022 902 178`. Cross-product occurrence census (same method, verified 2026-08-24): descriptors/embedded/optional/required — rider 141/1022/902/178 · clion 140/983/977/181 · phpstorm 143/1001/836/154 · webstorm 120/972/803/157 · rubymine 117/971/808/159 · pycharm 117/972/946/162 · rustrover 115/966/824/154 · phpstorm-light 106/939/781/154 · goland 90/949/827/150 · datagrip 61/887/601/145. **DataSpell DS-261.26222.84 ships ZERO descriptors in this format** — its jar is the older flat short-name generation (`lib.joni.xml`-style, no `plugins/` dir, no `loading=` attr): the format switch tracks the 262 platform line, so a port must detect which generation it faces before parsing.
**Retrieve:** (jar-resident manifest plane — not symbol-indexed)
```bash
unzip -p modules/module-descriptors.jar plugins/intellij.angular.plugin.xml
```

## Verdict
Adopt: three-level per-module gating declared at the module node inside each plugin descriptor, with the serialized binary as runtime truth and the XML as human-readable mirror. Adapt level vocabulary to your container. Omit concrete module lists (product content). Pairs with `module-descriptor-repository` (jar/dat substrate), `module-descriptor-split-grammar` (generated deps-only descriptor interior), and `module-set-load-levels` (lib-jar module-set layer).
