<!-- capsule-v2 -->
# inspection-description-catalog — where does a shipped IDE carry ~12,700 per-inspection help documents, and how are they keyed?

**Source:** JetBrains installed distributions (proprietary), PyCharm + WebStorm decisive instances. **Question:** How is the static-analysis rule catalog documented per-rule, and what's the key that ties doc → registration → suppression id?

## inspectionDescriptions/ resource dir inside module jars
**Path/Symbol:** `<module-jar>:inspectionDescriptions/<InspectionClassName>.html` (e.g. `intellij.python.psi.impl.jar:inspectionDescriptions/PyArgumentListInspection.html`, 97 files; `intellij.javascript.backend.jar`: 210 files).
**Signature:** HTML fragment: `<html><body><p>…reports…</p><p><b>Example:</b></p><pre><code>bad</code></pre>…good…</body></html>` — filename (minus .html) = class simple name = inspection `shortName` base (the stable profile/suppression key pinned in inspection-catalog-registration).
**Data Shape (cluster census, lib + plugin module jars):** pycharm insp=12,742 / inten=4,547 / msgs=4,730 · webstorm 12,614/4,433/4,635 · clion 12,925/4,799/4,759 · goland 12,717/4,608/4,630 · rustrover 12,816/4,676/4,640 · rubymine 12,713/4,592/4,641 · phpstorm 13,061/4,764/4,652 · phpstorm-light 12,978/4,682/4,593 · datagrip 12,172/3,935/4,559 · rider 12,647/4,483/4,742 · dataspell 11,642/3,973/4,216 · mps 1,059/573/192 · air 0/0/0.

### Decisive source
```html
<!-- inspectionDescriptions/PyArgumentListInspection.html -->
<html>
<body>
<p>Reports discrepancies between declared parameters and actual arguments, as well as
  incorrect arguments, for example, duplicate named arguments, and incorrect argument order.</p>
<p><b>Example:</b></p>
<pre><code>
class Foo:
    def __call__(self, p1: int, *, p2: str = "%"):
        return p2 * p1

bar = Foo()
bar.__call__() # unfilled parameter
</code></pre>
```

**Flow:** inspection registered via `localInspection` XML tag (`key="inspection.PyArgumentListInspection.display.name"` in the module's messages bundle) → settings page renders description by loading `inspectionDescriptions/<shortName-base>.html` from the inspection class's classloader → suppress annotations reference `shortName`; the HTML never carries ids itself.
**Invariant:** doc lookup is CLASSLOADER-RELATIVE and filename-keyed — renaming the class or moving the HTML to another jar breaks the settings-page description while inspections still run (silent doc loss). Bundles hold the display name; HTML holds only prose+examples; neither duplicates the other.
**Probe:** `python3 -c "import zipfile;z=zipfile.ZipFile('pycharm/plugins/python-ce/lib/modules/intellij.python.psi.impl.jar');n=[x for x in z.namelist() if x.startswith('inspectionDescriptions/')];print(len(n));print(z.read(n[2]).decode()[:120])"` → `97` + `<html>\n<body>\n<p>Reports discrepancies between declared parameters…`.
**Retrieve:** not symbol-indexed: `unzip -l <module-jar> | grep inspectionDescriptions | wc -l`.

## Verdict
Adopt: ship rule documentation as filename-keyed HTML fragments co-located with the rule's implementation jar, with i18n strings in property bundles — docs ride the same modular distribution as code. Adapt naming to your host's rule-id scheme. Omit JetBrains HTML styling conventions. Caveat: air ships none (thin layout), mps an order of magnitude fewer — scale follows language surface, not a fixed quota.
