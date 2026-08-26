<!-- capsule-v2 -->
# Keymap coverage audit grammar — why do keymap plugins register MORE action ids than they bind, and how do parent chains + chords complete the map?

**Source:** JetBrains IDE installed builds `WebStorm 262.9437.145` (`plugins/keymap-vscode/lib/keymap-vscode.jar:keymaps/VSCode.xml` [300 `<action id=`] + `keymaps/VSCode OSX.xml` [316]) and `Rider 262.8665.400` (`plugins/keymap-resharper/lib/keymap-resharper.jar:keymaps/ReSharper.xml` [75] over `keymap-visualStudio.jar:keymaps/Visual Studio.xml` [198]); Codebase Memory `jetbrains-webstorm`. **Question:** When porting a "switch to my editor's shortcuts" feature, what fraction of actions need explicit bindings, and what do empty entries mean?

## The three-layer answer
**Path/Symbol:** `VSCode.xml` — 300 total action entries: 164 with `<keyboard-shortcut>`/`<mouse-shortcut>`, **131 EMPTY self-closing** (`<action id="X"/>`); OS variant `VSCode OSX.xml` mirrors with `meta` for `ctrl`, adds 25 `meta k` two-stroke CHORDS (`first-keystroke="meta k" second-keystroke=...`) and 115 empties. Rider chain: `ReSharper.xml parent="Visual Studio"` (75/15) → `Visual Studio.xml parent="$default"` (198/37).
**Signature:** `<keymap version="1" name="N" parent="P" [disable-mnemonics="false"]>`; per action `<action id="ID"><keyboard-shortcut first-keystroke="K" [second-keystroke="K2"]/><mouse-shortcut keystroke="button4"/></action>`; plugin registration via `<bundledKeymap file="N.xml"/>` (VSCode ships 2 files, Eclipse 2, NetBeans 1, Visual Studio 2).
**Data Shape:** an entry WITHOUT children is a deliberate RESET: it shadows any parent-keymap binding so the foreign idiom stays silent (e.g. VSCode killing IntelliJ's own binding rather than inheriting it). Roughly HALF the registry is resets, not bindings — a porter who copies only bound ids loses ~44% of the semantic content.

### Decisive source
```xml
<!-- ReSharper chains onto Visual Studio, which chains onto the IDE default -->
<keymap name="ReSharper" parent="Visual Studio" version="1"  disable-mnemonics="false">
<!-- explicit reset: this action gets NO shortcut under VSCode, ignoring parents -->
<action id="ActivateMessagesToolWindow" />
<!-- chord: VSCode-style multi-stroke -->
<keyboard-shortcut first-keystroke="meta k" second-keystroke="meta w" />
```
Registration side (`keymap-vscode.jar:META-INF/plugin.xml`): only TWO lines — `<bundledKeymap file="VSCode.xml" />` + `<bundledKeymap file="VSCode OSX.xml" />`; no code at all.

**Flow:** user picks keymap → platform walks parent chain child→root collecting bindings → child's EMPTY entry stops inheritance for that id → first-keystroke+second-keystroke pairs form chords matched in order → OS variant file chosen by platform (its separate bundledKeymap line) remaps modifier vocabulary.
**Invariant:** keymap files are ID-REFERENCED DELTAS over the parent chain, never exhaustive maps; both bound AND reset entries are load-bearing. Wrong ports: treating empty tags as noise and stripping them (breaks reset semantics); assuming one file per keymap (OS variants are siblings registered separately); hardcoding ctrl/meta instead of shipping per-OS files.
**Probe:** deterministic reads: `grep -c '<action id=' keymaps/VSCode.xml` → 300; python count of self-closing `<action id="..."/>` → 131; `grep -c 'first-keystroke="meta k" second-keystroke' 'keymaps/VSCode OSX.xml'` → 25; `head -1 keymaps/ReSharper.xml` shows `parent="Visual Studio"`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-webstorm", query: "NodeJS keymap action", limit: 10, fields: ["signature", "name", "file"] });
```
(verified live: module node `jetbrains-webstorm.plugins.nodeJS` resolves; keymap jars are pure-resource — retrieve by direct unzip per Probe. Companion capsule `keymap-id-binding` owns the id-reference contract; `keymap-layering-contract` owns parent chains; THIS capsule adds the coverage/reset/chord arithmetic.)

## Verdict
Adopt delta-over-parent keymaps where silence is expressed by an explicit empty override; adapt chord syntax and OS-file split to host; omit mnemonic handling specifics. This closes pass-5's queued target #5 (keymap action-id coverage audit). Coverage caveat: resource-plane reads from jars on disk; counts verified by grep/python against the exact cited files.
