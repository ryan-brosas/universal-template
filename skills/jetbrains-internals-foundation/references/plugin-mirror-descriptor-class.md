<!-- capsule-v2 -->
# Plugin-mirror descriptor class — what are the `<plugin>`-rooted XMLs living INSIDE modules/module-descriptors.jar, and why must a parser dispatch on root tag before reading any attribute?

**Source:** JetBrains IDE installed build `PyCharm PY-262.9437.214` (proprietary distribution; study/reference use only), cross-product census over 10 v2-generation installs. **Question:** The jar looks like "one XML per module" — what is the second file class inside it, which schema does it follow, and what breaks if a porter greps the jar without separating the classes?

## Two schemas share one jar
**Path/Symbol:** `<ide>/modules/module-descriptors.jar:plugins/<module>.xml` — decisive instance `plugins/intellij.angular.plugin.xml` (whole file, 11 lines). Root-tag census over ALL 1,719 xml entries in PyCharm's jar: **1,602 `<module>`-rooted vs 117 `<plugin>`-rooted** — the `plugins/` prefix holds a DISTINCT schema, not merely a folder convention. Ownership split: `plugin-descriptor-loading-matrix` owns the `loading=` grammar on these files' children; THIS capsule owns the file-class boundary itself (what the files are, their root schema, their census, and the parse-dispatch invariant).
**Signature:** `<plugin id="<plugin-id>">` root (NOT `<module>`), carrying one self-referential `<plugin-descriptor-module name="..." namespace="$legacy_jps_module"/>` edge plus one `<module name="..." namespace="jetbrains" loading="embedded|optional|required"/>` child per code module.
**Data Shape:** children carry `name`+`namespace`+`loading` and NEVER `visibility` — the visibility tier (see `module-visibility-tier-grammar`) does not exist at this layer. Header comment on every file states the runtime truth lives in `module-descriptors.dat`: *"The IDE doesn't use this file; it takes data from module-descriptors.dat instead."*

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

**Flow:** build groups generated per-module descriptors under their owning plugin id → writes one `<plugin>`-rooted mirror per bundled plugin into `plugins/` → serializes everything into `.dat` for runtime → humans/diff tools read the XML mirrors.
**Invariant:** any jar-wide text sweep that does not first split entries by ROOT ELEMENT TAG conflates two schemas and fabricates phantom buckets — the recorded "none=117 visibility" defect class ([DONE:369] erratum) was exactly this: 117 plugin mirrors misread as visibility-less module descriptors. Parse rule: read the first element after the prolog/comments; route `<plugin>` roots to the loading-matrix grammar, `<module>` roots to the tier grammar. Second trap: `<module>` CHILDREN inside plugin mirrors have `name=` but their PARENT has none, so name-keyed joins must be depth-aware.
**Census (plugin-mirror count per product):** phpstorm 143 · rider 141 · clion 140 · webstorm 120 · pycharm 117 · rubymine 117 · rustrover 115 · goland 90 · datagrip 61 · dataspell 0 (DS-261 ships the older flat generation — no `plugins/` dir at all). The class exists only on the 262 platform line, same switch point as the loading-matrix format.
**Probe:** anchored at the PyCharm install root `/mnt/hdd/utopia/inspo/reference/jetbrains/pycharm` (strip prolog AND leading comment before reading the root tag — every mirror leads with `<?xml?>` + a comment; naive `find('<')` yields `?xml` for all 1,719 entries):
```bash
python3 -c "
import zipfile,re
from collections import Counter
z=zipfile.ZipFile('modules/module-descriptors.jar')
skip=re.compile(r'^\s*(<\?xml[^>]*\?>|<!--.*?-->)\s*')
c=Counter()
for n in z.namelist():
    if not n.endswith('.xml'): continue
    t=z.read(n).decode('utf-8','replace')
    while True:
        m=skip.match(t)
        if not m: break
        t=t[m.end():]
    i=t.find('<'); r=t[i:t.find('>',i)+1]
    c[r.split()[0].lstrip('<')]+=1
print(dict(c))"
```
→ `{'module': 1602, 'plugin': 117}`
**Retrieve:** (jar-resident manifest plane — not symbol-indexed)
```bash
unzip -l modules/module-descriptors.jar 'plugins/*' | tail -3
unzip -p modules/module-descriptors.jar plugins/intellij.angular.plugin.xml
```

## Verdict
Adopt: treat module-descriptors.jar as a TWO-SCHEMA container and make root-tag dispatch the first parse step; adopt the per-plugin grouping + self-referential plugin-descriptor-module edge as the readable mirror of the binary repository. Adapt the mirror-for-humans pattern to your own serialized registries (cheap diff surface beside the runtime blob). Omit concrete plugin lists. Pairs with `plugin-descriptor-loading-matrix` (child grammar), `module-visibility-tier-grammar` (why children carry no visibility), `module-descriptor-repository` (dat/jar substrate).
