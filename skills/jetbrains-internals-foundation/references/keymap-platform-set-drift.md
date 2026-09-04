<!-- capsule-v2 -->
# Platform keymap set drift — why do 262-train IDEs ship three different copies of the same ten keymaps?

**Source:** JetBrains IDE distributions (proprietary distribution), pins as in leaf Provenance pass 10; Codebase Memory `jetbrains-*` (resource plane, direct extraction). **Question:** Is the platform bundled keymap set identical across products on one release train, and if not, what exactly differs?

## Connected graph-selected seam
**Path/Symbol:** `lib/intellij.platform.ide.impl.jar` → `keymaps/` in every IDE except MPS (`lib/app.jar`); md5 over the sorted concatenation of the ten files.
**Signature:** set = {$default.xml, Default for GNOME.xml, Default for KDE.xml, Default for XWin.xml, Emacs.xml, Mac OS X 10.5+.xml, Mac OS X.xml, Sublime Text (Mac OS X).xml, Sublime Text.xml, macOS System Shortcuts.xml} — byte-identical FILE LIST everywhere; content digests differ.
**Data Shape:** THREE digest clusters over the 11 IDEs carrying `lib/intellij.platform.ide.impl.jar` (MPS ships its set in `app.jar`; air/dotmemory/dottrace ship NO keymaps): `fb04cc12…` {goland, phpstorm, phpstorm-light, pycharm, rubymine, rustrover, webstorm} · `9d0709a3…` {clion, datagrip, rider} · `9d211c2e…` {dataspell} (261-train). The clion/pycharm delta is EXACTLY a two-mouse-binding swap: `$default.xml:65` QuickEvaluateExpression `alt button1` (cl) vs `alt shift button1` (py) and the reciprocal swap on EditorAddOrRemoveCaret / EditorCreateRectangularSelectionOnMouseDrag — CLion gives plain alt-click to quick-evaluate, PyCharm keeps it as add-caret.

### Decisive source
```xml
<!-- $default.xml lines 63–66, CLion -->
<action id="QuickEvaluateExpression">
  <keyboard-shortcut first-keystroke="control alt F8"/>
  <mouse-shortcut keystroke="alt button1"/>
</action>
<!-- same range, PyCharm -->
<action id="QuickEvaluateExpression">
  <keyboard-shortcut first-keystroke="control alt F8"/>
  <mouse-shortcut keystroke="alt shift button1"/>
</action>
```
```text
md5 clusters (sorted-concat of 10 files):
  fb04cc12c635… goland phpstorm phpstorm-light pycharm rubymine rustrover webstorm
  9d0709a31e9f… clion datagrip rider
  9d211c2eb879… dataspell   [261-train]
```

**Flow:** platform build serves all IDEs from one source → product teams patch the shared `$default` for domain personality (debugger-centric CLion claims alt-click) → DataSpell's older-train copy additionally lacks the explicit RunAnything/SearchEverywhere gesture entries that 262 IDEs carry inside `$default` → result: "the platform default" is per-product, not per-build.
**Invariant:** the TEN-FILE SET and every map NAME are stable across the cluster (plugins can parent onto them portably); only binding CONTENTS drift by product. Any tooling that assumes byte-equality of platform resources across same-train IDEs is wrong; identity must be checked by digest.
**Probe:** `python3 - <<'EOF'\nimport zipfile, hashlib\nJB='$REFERENCE_ROOT/reference/jetbrains'\nfor prod in ['pycharm','clion','dataspell']:\n    with zipfile.ZipFile(f'{JB}/{prod}/lib/intellij.platform.ide.impl.jar') as z:\n        h=hashlib.md5()\n        for n in sorted(x for x in z.namelist() if x.startswith('keymaps/') and x.endswith('.xml')):\n            h.update(z.read(n))\n    print(prod, h.hexdigest()[:10])\nEOF` → pycharm fb04cc12c635 / clion 9d0709a31e9f / dataspell 9d211c2eb879.
**Coverage caveat:** resource plane, direct extraction; MPS set lives in app.jar (0 files in its ide.impl.jar).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "keymap shortcut action", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: treat the platform default keymap set as product-branded upstream with deliberate mouse-binding divergence; verify by digest, never by assumption. Adapt your host's equivalent branding points. Omit JetBrains' specific binding choices unless porting the exact UX.
