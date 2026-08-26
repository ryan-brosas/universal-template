<!-- capsule-v2 -->
# Editor notification provider plane — attribute-free banner registration

**Source:** JetBrains IDE installed builds `PyCharm PY-262.9437.214` / `WebStorm WS-262.9437.145` / `Rider RD-262.8665.400`; Codebase Memory `jetbrains-pycharm`. **Question:** Why does the highest-churn editor-banner EP carry NO attributes beyond implementation — and what does that force the porter to do?

## Zero-attribute contract
**Path/Symbol:** `intellij.platform.ide.impl.jar:META-INF/PlatformExtensionPoints.xml` — `<extensionPoint name="editorNotificationProvider" area="IDEA_PROJECT" interface="com.intellij.ui.EditorNotificationProvider" dynamic="true"/>`.
**Signature:** `<editorNotificationProvider implementation="<EditorNotificationProvider FQN>"/>` — 119/119 cluster declarations carry EXACTLY this one attribute (py 37, ws 38, rd 41).
**Data Shape:** all identity/visibility/condition logic lives in the CLASS (the provider returns `Function<PsiFile, JComponent>` per file or null); the manifest contributes nothing but class discovery. The EP is declared with `area="IDEA_PROJECT"` — project-scope only.

### Decisive source
```xml
<!-- intellij.platform.ide.impl.jar:META-INF/LangExtensions.xml:1233 -->
<editorNotificationProvider implementation="com.intellij.ide.GeneratedFileEditingNotificationProvider"/>
```

**Flow:** editor opens → platform queries every registered provider for that file → provider decides visibility in code (file type, project state, feature flags) and supplies the banner component.
**Invariant:** there is no declarative filter to port — porting this EP means porting the provider's per-file predicate too; a porter who expects manifest-level conditions will ship banners on wrong files. Wrong port: treating it like statusBarWidgetFactory (id+order) — none of those attributes exist here.
**Probe:** from install root: `for j in lib/*.jar; do unzip -p "$j" '*.xml' 2>/dev/null | grep -o '<editorNotificationProvider ' | wc -l; done | awk '{s+=$1} END{print s}'` → 37 (py), 41 (rd); declaration shape: `unzip -p lib/intellij.platform.ide.impl.jar META-INF/PlatformExtensionPoints.xml | grep -o '<extensionPoint name="editorNotificationProvider"[^>]*' | head -1` → contains `area="IDEA_PROJECT"`.

## Get live surrounding code
**Retrieve:** manifest-only plane — no BM25 symbol surface for this EP. Deterministic primitive:
```bash
unzip -p lib/intellij.platform.ide.impl.jar META-INF/LangExtensions.xml | grep -n 'GeneratedFileEditingNotificationProvider'
```
→ line 1233 at pin PY-262.9437.214.

## Verdict
Adopt code-side conditioning with a zero-attribute manifest row when your host separates discovery from policy; adapt provider signature; omit AWT/JComponent specifics. Coverage caveat: top-level-lib census. Boundary: tool-window docking lives in tool-window-registration; this capsule owns EDITOR-LEVEL banner surfaces.
