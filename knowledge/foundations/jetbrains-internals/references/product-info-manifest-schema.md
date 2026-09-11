<!-- capsule-v2 -->
# product-info-manifest-schema — what structured self-description does an installed IDE ship, and how should a porter read it?

**Source:** JetBrains installed distributions (proprietary; platform XML Apache-2.0 headers), Linux builds pinned per Provenance in SKILL.md; Codebase Memory `jetbrains-pycharm` etc. (resources NOT symbol-indexed — direct file reads). **Question:** Where does an installed IDE declare its identity, module/plugin inventory, file-type claims, and JVM bootstrap in machine-readable form?

## Product-info.json as the install's index card
**Path/Symbol:** `<ide>/product-info.json` (top-level JSON object, ~15 keys).
**Signature:** `{name, version, buildNumber, productCode, envVarBaseName, dataDirectoryName, svgIconPath, productVendor, majorVersionReleaseDate, minRequiredJavaVersion, launch[], customProperties[], bundledPlugins[], modules[], fileExtensions[], layout[]}`.
**Data Shape:** PyCharm instance: `name="PyCharm"`, `version="2026.2.1"`, `buildNumber="262.9437.214"`, `productCode="PY"`, `dataDirectoryName="PyCharm2026.2"` (settings/cache dir suffix = name+major.minor), `minRequiredJavaVersion=25`, `envVarBaseName` drives `$PYCHARM_*` env vars.

### Decisive source
```json
{"name":"PyCharm","version":"2026.2.1","buildNumber":"262.9437.214","productCode":"PY",
 "envVarBaseName":"PYCHARM","dataDirectoryName":"PyCharm2026.2","minRequiredJavaVersion":25,
 "modules":["com.intellij.jetbrains.rd.client","com.intellij.marketplace","com.intellij.ml.inline.completion", "...62 total"],
 "fileExtensions":["*-playbook.yaml","*-playbook.yml","*.ane","*.ant","*.apk","*.ats","...213 total"],
 "layout":[{"name":"AngularJS","kind":"plugin"},{"name":"fleet.andel","kind":"productModuleV2","classPath":["lib/fleet.andel.jar"]},
           {"name":"intellij.angular.backend","kind":"moduleV2","classPath":["plugins/angular-plugin/lib/modules/intellij.angular.backend.jar"]},
           {"name":"com.intellij.jetbrains.rd.client","kind":"pluginAlias"}, "..."]}
```

**Flow:** installer/toolbox writes product-info.json → launcher reads `launch[os/arch]` to pick JVM args + mainClass (see multi-persona-launcher-matrix) → platform resolves `modules[]` as always-loaded capability tokens → `fileExtensions[]` seeds file-type detection before plugins register richer types → `layout[]` maps every shipped artifact (four kinds: `plugin`, `pluginAlias`, `productModuleV2`, `moduleV2`) to its classpath jars → `customProperties` carries provenance (`source.git.revision=e3fceeafe8ef7`).
**Invariant:** `layout[].classPath` paths are relative to install root and are the ONLY authoritative jar→artifact mapping; `modules[]` ⊆ names appearing in `layout[]`/module-descriptors. A porter who invents a jar list instead of reading `layout` will miss split-module jars under `lib/modules/`.
**Probe:** `python3 -c "import json;d=json.load(open('pycharm/product-info.json'));print(len(d['layout']),d['dataDirectoryName'],len(d['fileExtensions']))"` → `1438 PyCharm2026.2 213`. Census across cluster (all full installs): pycharm 1438/62mods/213ext · rider 1450/64/379 · clion 1517/72/271 · webstorm 1289/57/189 · datagrip 986/53/112 · dataspell 884/51/144; air & mps ship NO layout/modules/fileExtensions (thin/legacy layouts).
**Retrieve:** not a graph seam (JSON not symbol-indexed): `python3 -c "import json;d=json.load(open('<ide>/product-info.json'));print(json.dumps({k:d[k] for k in ('name','buildNumber','productCode')},indent=1))"`.

## Verdict
Adopt the four-key manifest idea: identity+pin (buildNumber/productCode), inventory (`layout[]` kind/classPath), capability tokens (`modules[]`), and claimed surfaces (`fileExtensions[]`) as ONE self-described artifact — excellent shape for any pluggable app distribution. Adapt dir-suffix naming (`<Name><major>.<minor>`) to your host convention. Omit JetBrains-specific property values. Caveat: air/mps prove the schema degrades gracefully — fields may be absent on thin layouts.
