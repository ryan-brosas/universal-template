<!-- capsule-v2 -->
# Launcher script contract — how does the shell entry compose classpath, vmoptions, and identity properties?

**Source:** JetBrains IDE distributions (proprietary distribution; scripts Apache-2.0); study/reference use only. **Question:** What is the exact ordered algorithm a POSIX launcher follows to find JRE, merge user+default vmoptions (with GC/Xmx override filtering), assemble the boot classpath, and stamp product identity?

## Connected graph-selected seam
**Path/Symbol:** `pycharm/bin/pycharm.sh` (~263 CLASS_PATH assignments; same shape as webstorm.sh's 265).
**Signature:** JRE ladder `$<PRODUCT>_JDK` → `${CONFIG_HOME}/JetBrains/<Product><ver>/<product>.jdk` file → `$IDE_HOME/jbr` (arch-checked against `jbr/release` `OS_ARCH="..."`) → `$JDK_HOME`/`$JAVA_HOME` → `command -v java`.
**Data Shape:** vmoptions merge: default `bin/<product>64.vmoptions` + first-existing user override (`$<PRODUCT>_VM_OPTIONS` env → `<IDE_HOME>.vmoptions` (Toolbox) → config-dir file). If the USER file sets any `-XX:+.*GC`, `-Xms`, or `-XX:(Max|Min)RAMPercentage=`, those flags are FILTERED OUT of the default file before concatenation (`VM_FILTER` regex union). Identity: `-Didea.paths.selector=<Product><YY.M>` (config dir name), `-Didea.platform.prefix=<Product>`, `-Dintellij.platform.runtime.repository.path=$IDE_HOME/modules/module-descriptors.dat`, `-Djb.vmOptionsFile=…`, `-Xbootclasspath/a:$IDE_HOME/lib/nio-fs.jar`, system classloader forced to `com.intellij.util.lang.PathClassLoader`.

### Decisive source
```sh
VM_FILTER=""
if grep -E -q -e "-XX:\+.*GC" "$USER_VM_OPTIONS_FILE" ; then VM_FILTER="-XX:\+.*GC|"; fi
if grep -E -q -e "-XX:InitialRAMPercentage="  "$USER_VM_OPTIONS_FILE" ; then VM_FILTER="${VM_FILTER}-Xms|"; fi
if grep -E -q -e "-XX:(Max|Min)RAMPercentage=" "$USER_VM_OPTIONS_FILE" ; then VM_FILTER="${VM_FILTER}-Xmx|"; fi
VM_OPTIONS=$({ grep -E -v -e "(${VM_FILTER%'|'})" "$VM_OPTIONS_FILE"; cat "$USER_VM_OPTIONS_FILE"; } | grep -E -v -e "^#.*")
```
```
-Didea.paths.selector=PyCharm2026.2 -Didea.platform.prefix=Python com.intellij.idea.Main
```

**Flow:** tool check → JRE ladder → vmoptions merge with category-level override filter → explicit ~200-jar CLASS_PATH (platform-loader/util/product-backend first, then intellij.platform.*, then product modules) → exec java with --add-opens block + identity props + main class.
**Invariant:** user overrides win at FLAG-CATEGORY granularity, not per-line — setting MaxRAMPercentage suppresses BOTH Xms and Xmx from defaults; comments stripped everywhere. The selector string IS the user-data directory name — changing it orphans settings.
**Probe:** `grep -o 'idea.paths.selector=[A-Za-z0-9.]*' bin/pycharm.sh` → PyCharm2026.2; `diff clion64.vmoptions pycharm64.vmoptions` → only Xms + 3 welcome-screen props differ.
**Coverage caveat:** plain-shell deterministic probes; no test runner exists in installed builds.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "idea platform prefix paths selector startup", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: JRE discovery ladder, category-granular vmoptions override filtering, selector/prefix identity properties, module-descriptors path injection, forced PathClassLoader. Adapt flag names to your JVM/host. Extends pass-2's launcher-config-plane with the exact merge ALGORITHM (pass 2 recorded the md5 pairs; this capsule records why they pair).
