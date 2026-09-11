<!-- capsule-v2 -->
# Module visibility tier grammar — what do `visibility="internal|public|private"` on v2 module descriptors actually gate, and how is each tier distributed?

**Source:** JetBrains IDE installed build `PyCharm PY-262.9437.214` (proprietary distribution; study/reference use only), cross-product census over 10 v2-generation installs; Codebase Memory project `jetbrains-pycharm`. **Question:** When porting the module-repository idea, what access contract does each `visibility` tier express, who may consume whom, and what census must a porter reproduce to prove they parsed the right slice?

## The tier attribute and its three values
**Path/Symbol:** `<ide>/modules/module-descriptors.jar:<name>.xml` root element (`<module ...>`) — tier exemplars `intellij.libraries.asm.xml` (private), `intellij.libraries.batik.xml` (public), `fleet.multiplatform.shims.xml` (internal); consumer proof `intellij.platform.ide.impl.xml:59,:63`. Complements `module-descriptor-repository` (owns the jar/dat substrate) and `plugin-descriptor-loading-matrix` (owns the `plugins/*.xml` layer): THIS capsule owns the per-module visibility contract on true `<module>`-rooted descriptors.
**Signature:** `<module name="<id>" namespace="jetbrains" visibility="internal|public|private">` — exactly three values exist cluster-wide; there is no default/absent case.
**Data Shape:** the attribute sits ONLY on the root element of module-rooted descriptors (top-level `*.xml`, plus `$legacy_jps_module`/`$legacy_jps_library`/`$implicit` shim slices). It NEVER appears on `<module>` children inside `<plugin>`-rooted mirrors (see `plugin-mirror-descriptor-class`) and NEVER coexists with `loading=` (different layer). Spelling is uniformly tight `visibility="`; EVERY `<module>`-rooted descriptor in the jar carries it — zero attribute-absent cases (verified full-strata pycharm+rider). Tier correlates with slice kind: `$legacy_jps_module` shims are ALL public (pycharm 236), `$legacy_jps_library` shims ALL public (117), `$implicit` synthetics ALL private (23); only plain descriptors spread across all three tiers.

### Decisive source
```xml
<!-- intellij.libraries.asm.xml (root; whole file is deps-only below it) -->
<module name="intellij.libraries.asm" namespace="jetbrains" visibility="private">
<!-- intellij.libraries.batik.xml -->
<module name="intellij.libraries.batik" namespace="jetbrains" visibility="public">
<!-- fleet.multiplatform.shims.xml -->
<module name="fleet.multiplatform.shims" namespace="jetbrains" visibility="internal">
<!-- intellij.platform.ide.impl.xml dependencies body — a PUBLIC module consuming PRIVATE targets -->
    <module name="intellij.libraries.asm"/>          <!-- :59 -->
    <module name="intellij.libraries.blockmap"/>     <!-- :63 -->
```

**Flow:** build emits one descriptor per module with its tier → boot resolves each `<dependencies><module name=X/></dependencies>` edge against X's tier keyed by the CONSUMER's identity → public accepts any consumer, internal accepts platform-family consumers, private accepts same-namespace consumers.
**Invariant (consumer-side shape of the packaging policy):** over PyCharm's full dependency graph — internal targets receive 5,850 inbound edges from `intellij.`-prefixed consumers + 70 from `fleet.`-prefixed, ZERO from anything else, and every one of the 420 internal modules has ≥1 inbound consumer (no dead tier); private-target pairs are 971/971 same-FIRST-LABEL (`intellij.libraries.asm` ← `intellij.platform.ide.impl`, `intellij.database.impl`, `intellij.platform.serviceContainer`, plus legitimate self-dependencies `intellij.libraries.blockmap` → itself); third-party dependents (`io.`/`eclipse.`/`github.` labels) appear exclusively behind public targets. Reconciliation with `module-visibility-tiers` (sibling pass 9, same-cycle): tiers are packaging metadata, NOT a runtime access lattice — outbound edges cross tiers freely (e.g. public `intellij.platform.ide.impl` :59/:63 consumes private libraries); what this capsule adds is the EMPIRICAL consumer-side closure the policy produces: who actually ends up allowed to consume each tier once names encode ownership. Enforcement vocabulary (ModuleVisibility enums + check-option severity ladder) lives in that capsule.
**Census (plain top-level slice, per product internal/public/private of total):** pycharm 420/301/505 of 1,226 · webstorm 352/268/469 of 1,089 · rider 409/298/506 of 1,213 · clion 442/308/533 of 1,283 · goland 359/265/483 of 1,107 · phpstorm 354/265/480 of 1,099 · rubymine 355/267/467 of 1,089 · rustrover 362/268/477 of 1,107 · datagrip 312/221/334 of 867 · dataspell n/a (older flat generation, no tiers). Shim slices add deterministic tiers: pycharm +236 public (`$legacy_jps_module`) +117 public (`$legacy_jps_library`) +23 private (`$implicit`) — so a WHOLE-module-root sweep yields 420/654/528 and a NAMED-roots-only sweep 420/418/528; both are correct over different slices, which is why the slice must be named.
**Probe:** anchored at the PyCharm install root `$REFERENCE_ROOT/reference/jetbrains/pycharm` (the prolog+comment strip loop is LOAD-BEARING: a naive `find('<')` classifies every file as `?xml`, a naive post-`?>` skip misreads the 117 comment-led mirrors as `<!--`):
```bash
python3 -c "
import zipfile,re
z=zipfile.ZipFile('modules/module-descriptors.jar')
skip=re.compile(r'^\s*(<\?xml[^>]*\?>|<!--.*?-->)\s*')
c={'internal':0,'public':0,'private':0}; plug=0
for n in z.namelist():
    if not n.endswith('.xml'): continue
    t=z.read(n).decode('utf-8','replace')
    while True:
        m=skip.match(t)
        if not m: break
        t=t[m.end():]
    i=t.find('<'); r=t[i:t.find('>',i)+1]
    tag=r.split()[0].lstrip('<')
    if tag=='plugin': plug+=1; continue
    m=re.search(r'visibility\s*=\s*\"([^\"]*)\"',r)
    if m: c[m.group(1)]+=1
print(c,plug)"
```
→ `{'internal': 420, 'public': 654, 'private': 528} 117` (whole-module-root slice + plugin-mirror count; subtract the shim strata above to recover any sub-slice).
**ERRATUM ([DONE:369] second-worker lane):** the pass-4 recorded baseline "internal=420, public=301, private=528, none=117" mixed three counting slices: 420/301 are plain-slice EXACT and stand; private=528 had silently included 23 legacy-shim privates (plain private = 505); **"none=117" was never a visibility bucket** — it counted the `<plugin>`-rooted mirror files, whose nested `<module>` children carry no visibility attribute. A loose `grep 'visibility="'` sweep cannot produce these numbers correctly because it also counts `visibility=` tokens inside dependency bodies and prose. Always dispatch on ROOT ELEMENT TAG first.

**Retrieve:** (jar-resident manifest plane — not symbol-indexed)
```bash
unzip -p modules/module-descriptors.jar intellij.libraries.asm.xml | head -1
codebase-memory-mcp cli search_graph '{"project":"jetbrains-pycharm","query":"module-descriptors","limit":3,"detail":"ids"}'
```
(the graph resolves the repository plane at file granularity; tier interiors live only in the jar).

## Verdict
Adopt: three-tier visibility declared per module root, enforced through dependency resolution keyed on consumer namespace prefix, with platform-internal as the largest gated tier (~31–34% of plain modules per product) and zero absent-attribute cases. Adapt the tier vocabulary to your container's trust model. Omit JetBrains' concrete tier assignments. Pairs with `module-descriptor-repository` (substrate), `plugin-descriptor-loading-matrix` (per-plugin layer + load levels), `implicit-module-synthesis` (the $implicit slice this census includes in its shim accounting).
