<!-- capsule-v2 -->
# Keymap OS-variant matrix — how do base/OSX pairs and cross-plugin parent chains compose into one graph?

**Source:** JetBrains IDE distributions 262-train (proprietary distribution; plugin.xml Apache-2.0-marked), pins as in leaf Provenance pass 10; Codebase Memory `jetbrains-*` (resource plane, direct extraction). **Question:** What is the complete parent graph over all bundled keymaps cluster-wide, and what does a porter get wrong about OS variants?

## Connected graph-selected seam
**Path/Symbol:** every `keymaps/*.xml` root tag across `<product>/lib/intellij.platform.ide.impl.jar` (MPS: `lib/app.jar`) and all 32 `<product>/plugins/keymap-*/lib/keymap-*.jar`.
**Signature:** `<keymap version="1" name="X" [parent="P"] disable-mnemonics="true|false">` — attribute order VARIES between files; `parent` optional; `version` always "1".
**Data Shape:** per-install FILE INSTANCES cluster-wide: 10 platform maps × 11 IDEs carrying `lib/intellij.platform.ide.impl.jar` + **55** plugin-map instances across the 32 keymap plugin dirs (= 24 `parent="$default"` + 21 `parent="Mac OS X 10.5+"` + 5 `parent="Visual Studio"` + 4 `parent="Visual Studio OSX"` + 1 legacy `parent="Mac OS X"`) + MPS's own 10-file copy inside `lib/app.jar`; air/dotmemory/dottrace ship NO keymap files anywhere. DISTINCT map names = 26 (10 platform + 16 foreign-editor names incl. OSX variants). Parent edges: `$default` ← {Default for XWin, Emacs, Mac OS X, Mac OS X 10.5+, Sublime Text, Eclipse, NetBeans 6.5, QtCreator, Visual Studio}; `Mac OS X 10.5+` ← {Default for GNOME/KDE (via XWin), macOS System Shortcuts, Sublime Text (Mac OS X), Eclipse (Mac OS X), QtCreator (Mac OS X), Visual Studio OSX, Xcode, VSCode OSX}; **cross-plugin chains**: `Visual Studio` ← {ReSharper, Visual Assist, Visual Studio 2022} and `Visual Studio OSX` ← {ReSharper OSX, Visual Assist OSX}; legacy outlier: TextMate → `Mac OS X` (NOT 10.5+). `disable-mnemonics=true` on ALL mac-family platform maps (Mac OS X, 10.5+, macOS System Shortcuts) and false on every foreign-editor map.

### Decisive source
```xml
<!-- platform OS variant: re-parents + flips mnemonics off -->
<keymap name="Mac OS X 10.5+" parent="$default" version="1" disable-mnemonics="true">   <!-- 800 lines vs $default 1319 -->
<!-- third-party OSX pair rides the mac chain, not its own base -->
<keymap name="Eclipse (Mac OS X)" disable-mnemonics="false" parent="Mac OS X 10.5+">
<keymap name="Eclipse" disable-mnemonics="false" parent="$default">
<!-- CROSS-PLUGIN CHAIN: ReSharper parents onto another PLUGIN's map name -->
<keymap name="ReSharper" parent="Visual Studio" version="1"  disable-mnemonics="false">
<keymap name="Visual Assist OSX" parent="Visual Studio OSX" version="1" disable-mnemonics="false">   <!-- 32 lines only -->
```

**Flow:** resolution walks `name → parent` recursively to `$default`; an OS-paired foreign map therefore inherits mac remaps from `Mac OS X 10.5+` rather than duplicating them; a derived editor scheme (ReSharper/VisualAssist/VS2022) layers onto the Visual Studio plugin's names so installing it WITHOUT the VS plugin would dangle — which is exactly why VS2022's descriptor carries `<depends>com.intellij.plugins.visualstudiokeymap</depends>` while ReSharper/VisualAssist ship alongside their own bundled VisualStudio copies.
**Invariant:** parent references are by NAME STRING across jar boundaries — no namespace, no import; two plugins may not define the same map name, but any plugin may PARENT onto another's name provided the dependency is guaranteed by packaging or `<depends>`. Line-count asymmetry is the override-only economy: VSCode OSX 789 lines still far below $default's 1319.
**Probe:** `for p in $REFERENCE_ROOT/reference/jetbrains/*/plugins/keymap-*; do unzip -p $p/lib/*.jar 'keymaps/*' 2>/dev/null | grep -o 'parent="[^"]*"'; done | sort | uniq -c | sort -rn | head -8` → top edge `parent="$default"` then `parent="Mac OS X 10.5+"`; single-source check `unzip -p $REFERENCE_ROOT/reference/jetbrains/clion/plugins/keymap-resharper/lib/keymap-resharper.jar 'keymaps/ReSharper.xml' | grep -c 'parent="Visual Studio"'` → 1.
**Coverage caveat:** resource plane, direct extraction.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-rider", query: "keymap shortcut action", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: name-string parent chains with explicit plugin-level `<depends>` for cross-plugin bases, and the OS-pair convention (two files, one per desktop, both declared via separate EPs). Adapt which OS variants you need. Omit JetBrains' actual binding tables.
