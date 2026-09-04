<!-- capsule-v2 -->
# bundled-plugin-exact-pin — why does every bundled plugin declare since-build == until-build == product buildNumber?

**Source:** JetBrains installed distributions (proprietary), PyCharm decisive instances (markdown, ini plugins) + code-provenance. **Question:** What version-range contract keeps an install's plugin set coherent, and what breaks it?

## META-INF/plugin.xml idea-version exact pin
**Path/Symbol:** `pycharm/plugins/markdown/lib/intellij.markdown.jar:META-INF/plugin.xml` → `<idea-version since-build="262.9437.214" until-build="262.9437.214"/>` and `<version>262.9437.214</version>`; identical pattern in `plugins/ini/lib/ini.jar`, `code-provenance`.
**Signature:** `since-build == until-build == <product buildNumber>` for every bundled plugin jar that carries a top-level plugin.xml; marketplace-installed plugins use ranges instead (not present in these clean installs).
**Data Shape:** module jars WITHOUT their own plugin.xml (e.g. `intellij.json.syntax.jar`) carry only `<name>.kotlin_module` markers — the pin lives at the PLUGIN level, not per module.

### Decisive source
```xml
<!-- plugins/markdown/lib/intellij.markdown.jar:META-INF/plugin.xml -->
<version>262.9437.214</version>
<idea-version since-build="262.9437.214" until-build="262.9437.214" />
```

**Flow:** platform loads bundled plugin → compatibility check compares host buildNumber against [since,until] → exact equality always passes inside the matched install → any external mixing (copying a plugin dir across IDE versions) fails the check by design.
**Invariant:** the pin makes the ENTIRE install atomic — plugins are build artifacts of the same release train as the platform, which is WHY the cluster-parity md5 trick (cluster-platform-parity-note) works: shared-platform files hash identically only within one train. A porter distributing "compatible" plugin sets must either adopt exact pins or implement range semantics deliberately.
**Probe:** `python3 -c "import zipfile,re;z=zipfile.ZipFile('pycharm/plugins/markdown/lib/intellij.markdown.jar');px=z.read('META-INF/plugin.xml').decode();print(re.search(r'<idea-version[^/]*/>',px).group(0));print(re.search(r'<version>[^<]+',px).group(0))"` → both `262.9437.214`.
**Retrieve:** not symbol-indexed: `unzip -p <plugin-jar> META-INF/plugin.xml | grep idea-version`.

## Verdict
Adopt exact-pin versioning for anything distributed INSIDE a product release; reserve ranges for externally installed artifacts. Adapt the attribute vocabulary (`since/until`). Omit marketplace update-flow specifics. Caveat: verified on 3 representative plugins; treat as universal after one `grep -r 'until-build' --include=plugin.xml` spot-check on your own target set.
