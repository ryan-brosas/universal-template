<!-- capsule-v2 -->
# message-bundle-per-module — how do ~4,700 i18n property bundles partition a product without key collisions?

**Source:** JetBrains installed distributions (proprietary), PyCharm python-ce plane decisive instance. **Question:** What is the unit of i18n packaging, and what key-namespace discipline keeps thousands of bundles mergeable?

## messages/<XxxBundle>.properties, one primary bundle per module
**Path/Symbol:** `intellij.python.community.impl.jar:messages/PyBundle.properties` (1,578 keys / 1,864 lines); one-bundle-per-module across the cluster: PyPsiBundle (psi.impl), PyBlackBundle (black), PyCondaBundle (conda), PipEnvBundle, PyPoetryBundle, PyInterpreterBundle, PySdkBundle, RuffBundle, TyBundle, PyreflyBundle… (33+ distinct bundles in the python-ce plugin alone; 4,559–4,759 messages files per full install).
**Signature:** `key.with.dots=<message>`; keys grouped by prefix family: `QFIX.NAME.*`, `QFIX.FAMILY.NAME.*`, `sdk.configuration.path.*`, `inspection.<Class>.display.name`, `action.<Id>.text`.
**Data Shape:** flat `key=value` with `\n`/`\'` escapes and `{0}`-style MessageFormat placeholders; NO nesting, NO per-locale variants shipped in the base install (localization rides separate plugins — see localization-overlay-plugin).

### Decisive source
```properties
# messages/PyBundle.properties — representative key families
QFIX.add.import.add.import=Add import
QFIX.NAME.implement.methods=Implement methods
QFIX.FAMILY.NAME.rename.element=Rename Element
sdk.configuration.path.remote.not.supported=Remote SDK ''{0}'' is not supported
action.PyPackageToolbarAdditional.text=Python Packages
```

**Flow:** code references `PyBundle.message("sdk.configuration.path.invalid", path)` → runtime resolves bundle by short class name (`messages.PyBundle`) inside the module's classloader → each module's XML descriptors declare `resource-bundle="messages.XxxBundle"` where needed → settings/intentions/inspections point at the same bundles via `bundle=` attributes.
**Invariant:** ONE canonical bundle per module named for its domain (never shared across modules) — cross-module text reuse happens by convention of key prefixes, not by importing another module's bundle. Because lookup is classloader-relative, two modules MAY both ship `messages/FooBundle.properties` without collision; a porter who centralizes all strings into one global file breaks modular reuse and hot-unload.
**Probe:** `python3 -c "import zipfile;z=zipfile.ZipFile('pycharm/plugins/python-ce/lib/modules/intellij.python.community.impl.jar');d=z.read('messages/PyBundle.properties').decode();ks=[l.split('=')[0] for l in d.splitlines() if '=' in l];print(len(ks),ks[0],ks[-1])"` → `1578 QFIX.add.import.add.import action.PyPackageToolbarAdditional.text`.
**Retrieve:** not symbol-indexed: `unzip -l <module-jar> | grep 'messages/.*properties'`.

## Verdict
Adopt: i18n granularity = deployment granularity; name bundles after their owning domain and namespace keys by feature family (QFIX./sdk./action.). Adapt escaping/pluralization to host framework. Omit JetBrains MessageFormat specifics beyond `{0}` placeholders. Caveat: counts move every release; re-run the probe rather than trusting these numbers.
