<!-- capsule-v2 -->
# Status bar widget factory registration — id-keyed widgets with anchor-sequenced placement

**Source:** JetBrains IDE installed builds `PyCharm PY-262.9437.214` / `WebStorm WS-262.9437.145` / `Rider RD-262.8665.400`; Codebase Memory `jetbrains-pycharm`. **Question:** How does the platform decide where a status bar widget sits — and why do most declarations carry no placement at all?

## Widget factory contract
**Path/Symbol:** `intellij.platform.ide.impl.jar:META-INF/PlatformExtensionPoints.xml` — `<extensionPoint name="statusBarWidgetFactory" interface="com.intellij.openapi.wm.StatusBarWidgetFactory" dynamic="true"/>`.
**Signature:** `<statusBarWidgetFactory id="<widget-id>" implementation="<StatusBarWidgetFactory FQN>" [order="<first|last|after|before <anchor-id>(, ...)"]/>`.
**Data Shape:** `id` REQUIRED (134/134 cluster) — it is both the registry key and the ANCHOR other widgets sequence against; `order` present on only 33 of 41 py declarations (80%) and 109 cluster-wide; anchors are OTHER WIDGET IDS, comma-composable: `order="after Position, after AIAssistant, before LineSeparator"`.

### Decisive source
```xml
<!-- intellij.platform.commercial.jar:intellij.platform.commercial.xml:32 -->
<statusBarWidgetFactory id="NonCommercial" implementation="com.intellij.ide.ui.NonCommercialFactory" order="last"/>
<!-- py order vocabulary (occurrence census): last x4, after ReadOnlyAttribute x2,
     after PowerSaveMode x2, after LineSeparator x2, after InsertOverwrite x2, first x1 ... -->
```

**Flow:** factories register by id → platform orders widgets: explicit `order` chain first (anchors resolved against already-known ids), unordered entries fill remaining slots → presentation layer renders per-frame.
**Invariant:** a widget id is GLOBAL namespace — two factories with one id collide; an `order` referencing a nonexistent anchor degrades to unspecified position (same degrade rule as extension-ordering-attributes). Wrong port: generating auto-ids (breaks third-party anchoring) or assuming order is mandatory.
**Probe:** from install root: `for j in lib/*.jar; do unzip -p "$j" '*.xml' 2>/dev/null | grep -o '<statusBarWidgetFactory ' | wc -l; done | awk '{s+=$1} END{print s}'` → 41 (py), 43 (ws), 50 (rd); ordered subset py: `... | grep '<statusBarWidgetFactory ' | grep -c 'order="'` → 17.

## Get live surrounding code
**Retrieve:** manifest-only plane — no BM25 symbol surface for this EP. Deterministic primitive:
```bash
unzip -p lib/intellij.platform.commercial.jar intellij.platform.commercial.xml | grep -n 'NonCommercialFactory'
```
→ line 32 at pin PY-262.9437.214.

## Verdict
Adopt id-as-anchor sequencing with optional placement (default = end/unspecified); adapt widget lifecycle to host; omit IntelliJ's multi-frame widget presentation internals. Coverage caveat: top-level-lib census only. Boundary: general ordering grammar owned by extension-ordering-attributes; this capsule owns the STATUS-BAR-SPECIFIC id/anchor economics.
