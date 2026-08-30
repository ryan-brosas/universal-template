<!-- capsule-v2 -->
# Keymap layering contract — how do OS variants and foreign-editor maps compose without duplicating shortcuts?

**Source:** JetBrains IDE distributions (proprietary distribution; plugin.xml Apache-2.0-marked); study/reference use only; Codebase Memory `jetbrains-pycharm`. **Question:** How is a keymap tree structured so platform defaults, OS-specific variants, and third-party editor emulations each override only what differs — and how do keymap plugins declare themselves?

## Connected graph-selected seam
**Path/Symbol:** `lib/intellij.platform.ide.impl.jar` → `keymaps/$default.xml`, `keymaps/Mac OS X 10.5+.xml`, `keymaps/{Default for GNOME|KDE|XWin,Emacs,Sublime Text*,macOS System Shortcuts}.xml`; rider: `plugins/keymap-resharper/lib/keymap-resharper.jar`.
**Signature:** `<keymap name="Mac OS X 10.5+" parent="$default" version="1" disable-mnemonics="true">`; registration via `<extensions defaultExtensionNs="com.intellij"><bundledKeymap file="ReSharper.xml" /></extensions>`.
**Data Shape:** per-action entries with three shortcut kinds: `<keyboard-shortcut first-keystroke="meta UP"/>`, `<mouse-shortcut keystroke="alt button1 doubleClick"/>`, `<keyboard-gesture-shortcut keystroke="shift SHIFT" modifier="dblClick"/>` (double-tap gestures). Files reference actions BY ID ONLY — no class, no label.

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
```xml
<keymap name="ReSharper" parent="Visual Studio" version="1" disable-mnemonics="false">
  <action id="ChangeSignature"><keyboard-shortcut first-keystroke="control F6"/></action>
```
```xml
<bundledKeymap file="ReSharper.xml" />
```

**Flow:** `$default` defines the canonical set → OS variants (`Mac OS X 10.5+`, GNOME/KDE/XWin) re-parent to `$default` and override only differences (plus `disable-mnemonics` on mac) → emulation keymaps chain further (`ReSharper → Visual Studio`) → a keymap PLUGIN declares files via bundledKeymap EP and may depend on another keymap plugin (`<depends>com.intellij.plugins.visualstudiokeymap</depends>`).
**Invariant:** an action id referenced but never defined in any ancestor silently has NO binding — the id-only grammar makes typos invisible; chains must resolve through named parents that exist at load time.
**Probe:** `unzip -p lib/intellij.platform.ide.impl.jar 'keymaps/Mac OS X 10.5+.xml' | head -2` → parent="$default"; rider jar's plugin.xml pins `since==until==262.8665.400` + Category=Keymap.
**Coverage caveat:** resource plane, direct extraction.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-rider", query: "keymap shortcut action", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: parent-chain keymaps with delta-only overrides, gesture+mouse+keyboard triple vocabulary, id-referenced bindings, keymap-as-plugin packaging with cross-keymap depends. Adapt the action-id namespace. Omit concrete shortcut tables. Cluster census: every 262 IDE ships the identical 10-file platform set in intellij.platform.ide.impl.jar; rider adds 9 VS-family files across 5 tiny plugins.
