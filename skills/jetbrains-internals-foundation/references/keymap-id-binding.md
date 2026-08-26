<!-- capsule-v2 -->
# Keymap structure — id-referenced shortcuts with layered override maps

**Source:** JetBrains IDE installed build `PyCharm 262.9437.214`; Codebase Memory `jetbrains-pycharm`. **Question:** How do keymaps bind shortcuts to commands without duplicating command definitions, and how do platform variants layer?

## Keymap files
**Path/Symbol:** `lib/intellij.platform.ide.impl.jar:keymaps/$default.xml` (46KB) + `keymaps/{Mac OS X, Mac OS X 10.5+, Emacs, Sublime Text, Sublime Text (Mac OS X), Default for GNOME/KDE/XWin, macOS System Shortcuts}.xml` + `idea/PlatformActions.xml` + `idea/PyCharmCoreApplicationInfo.xml`.
**Signature:** `<keymap name="$default" version="1" disable-mnemonics="false"><action id="A"><keyboard-shortcut first-keystroke="ctrl S"/><mouse-shortcut keystroke="button3 doubleClick"/></action></keymap>`.
**Data Shape:** bindings reference ACTION IDS only (no classes); multiple shortcut kinds per action (keyboard/mouse/gesture); OS-specific maps rebind the same ids; `disable-mnemonics` is a map-level behavior switch.

### Decisive source
```xml
<keymap name="$default" version="1" disable-mnemonics="false">
  <action id="SearchEverywhere">
    <keyboard-gesture-shortcut keystroke="shift SHIFT" modifier="dblClick"/>
  </action>
  <action id="OpenInRightSplit">
    <keyboard-shortcut first-keystroke="shift ENTER"/>
    <mouse-shortcut keystroke="alt button1 doubleClick"/>
  </action>
```

**Flow:** actions register ids in descriptor XML → each keymap binds shortcuts per id → active keymap resolves at runtime; user edits overlay on top.
**Invariant:** decoupling is total — a keymap file contains ZERO implementation references; renaming an action id silently orphans every keymap binding. Wrong port: embedding handler classes inside keymap data "for convenience".
**Probe:** deterministic: `unzip -p intellij.platform.ide.impl.jar 'keymaps/$default.xml' | head -12` shows id-only bindings incl. gesture shortcuts.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "keymap shortcut action", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt pure id-referenced binding tables with layered variant maps; adapt shortcut grammar; omit IntelliJ keystore conflict resolution. Coverage caveat: direct jar read.
