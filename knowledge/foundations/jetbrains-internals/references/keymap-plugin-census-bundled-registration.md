<!-- capsule-v2 -->
# Keymap plugin census & bundledKeymap registration — how does an IDE ship foreign-editor keymaps as optional plugins?

**Source:** JetBrains IDE distributions 262-train (proprietary distribution; plugin.xml Apache-2.0-marked), pins py 262.9437.214 / cl .136 / ws .145 / ps .196 / go .195 / rm .192 / rr .161 / dg .163 / rd 262.8665.400 / ds 261.26222.84 / psl 262.9421 / mps MPS-261.25134.779 / air 262.132.35; Codebase Memory `jetbrains-*` (resource plane — jar interiors are NOT symbol-indexed, mined by direct zip extraction). **Question:** Which keymap plugins ship in which IDEs, and what is the exact descriptor contract that registers a bundled keymap?

## Connected graph-selected seam
**Path/Symbol:** `<product>/plugins/keymap-*/lib/keymap-*.jar` → `META-INF/plugin.xml` + `keymaps/*.xml`.
**Signature:** `<extensions defaultExtensionNs="com.intellij"><bundledKeymap file="Eclipse.xml" /><bundledKeymap file="Eclipse (Mac OS X).xml" /></extensions>` inside `<idea-plugin>` with `<category>Keymap</category>`, `<depends>com.intellij.modules.lang</depends>`, and `idea-version since-build == until-build == <own version>`.
**Data Shape:** 32 keymap plugin dirs over EXACTLY 8 IDEs — zero in pycharm, dataspell, datagrip, mps, air, dotmemory, dottrace. Per-product counts: rustrover 7 · clion 6 · rider 5 · phpstorm 4 · webstorm 4 · rubymine 4 · goland 1 · phpstorm-light 1. Per-family product sets: Eclipse {cl,ps,rm,rr,ws} · NetBeans 6.5 {cl,ps,rm,rr,ws} · Visual Studio {cl,ps,rm,rr,ws,rider} · VSCode {go,ps,psl,rider,rr,ws} · ReSharper {cl,rider,rr} · QtCreator {cl,rr} · Xcode {cl,rr} · TextMate {rm only} · Visual Assist {rider only} · Visual Studio 2022 {rider only}. Each jar holds exactly its declared map files: 1-file plugins (NetBeans, Xcode, TextMate, VS2022) vs 2-file OS-paired plugins (Eclipse/QtCreator/ReSharper/VisualStudio/VisualAssist/VSCode = base + OSX variant).

### Decisive source
```xml
<idea-plugin>
  <name>Eclipse Keymap</name>
  <id>com.intellij.plugins.eclipsekeymap</id>
  <version>262.9437.136</version>
  <idea-version since-build="262.9437.136" until-build="262.9437.136" />
  <vendor>JetBrains</vendor>
  <category>Keymap</category>
  <description><![CDATA[Eclipse keymap for all IntelliJ-based IDEs.
  Use this plugin if Eclipse keymap is not pre-installed in your IDE.]]></description>
  <depends>com.intellij.modules.lang</depends>
  <extensions defaultExtensionNs="com.intellij">
    <bundledKeymap file="Eclipse.xml" />
    <bundledKeymap file="Eclipse (Mac OS X).xml" />
  </extensions>
</idea-plugin>
```
```xml
<!-- rider/plugins/keymap-visualStudio2022 — plugin-to-plugin dependency chain -->
<depends>com.intellij.modules.lang</depends>
<depends>com.intellij.plugins.visualstudiokeymap</depends>
<extensions defaultExtensionNs="com.intellij">
  <bundledKeymap file="Visual Studio 2022.xml" />
</extensions>
```

**Flow:** install ships zero or more `keymap-*` plugin dirs → each jar's plugin.xml declares category=Keymap + lang-module dependency → each `bundledKeymap` EP names ONE keymap file resolved relative to the jar root (`keymaps/` dir) → since==until==own-version exact-pinning makes every rebuild re-release the whole set → a derived keymap (VS2022) adds a `<depends>` on its base keymap plugin so the parent NAME resolves at load.
**Invariant:** a bundledKeymap file name is jar-root-relative and must match a packaged `keymaps/<file>` exactly — there is no fallback lookup; and the OS pairing is by-convention two separate bundledKeymap declarations, never one file with conditionals.
**Probe:** `unzip -p $REFERENCE_ROOT/reference/jetbrains/clion/plugins/keymap-eclipse/lib/keymap-eclipse.jar META-INF/plugin.xml | grep -c bundledKeymap` → 2; `for d in $REFERENCE_ROOT/reference/jetbrains/*/plugins/keymap-*; do basename $d; done | wc -l` → 32.
**Coverage caveat:** resource plane, direct extraction; jar-resident freshness not symbol-indexed (expected class).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-clion", query: "keymap plugin bundledKeymap", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: the one-EP-per-map-file registration form, exact since/until self-pinning, and parent-keymap plugin dependency for derived maps. Adapt the family selection to your product's audience (JetBrains ships VS families only where .NET/dev users expect them). Omit the actual shortcut tables (third-party editor data).
