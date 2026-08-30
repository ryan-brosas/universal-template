<!-- capsule-v2 -->
# Editor action handler interception — how keybinding-time behavior is replaced without touching the action itself

**Source:** JetBrains IDE installed builds `PyCharm PY-262.9437.214` / `WebStorm WS-262.9437.145` / `Rider RD-262.8665.400`; Codebase Memory `jetbrains-pycharm`. **Question:** When two plugins want to intercept the same editor action's execution, which declaration wins and what must a porter copy so interception composes instead of breaking?

## Interceptor chain grammar
**Path/Symbol:** `intellij.platform.ide.impl.jar:META-INF/PlatformExtensionPoints.xml` — `<extensionPoint name="editorActionHandler" beanClass="com.intellij.openapi.editor.actionSystem.EditorActionHandlerBean" dynamic="true">` with `<with attribute="implementationClass" implements="com.intellij.openapi.editor.actionSystem.EditorActionHandler"/>`.
**Signature:** `<editorActionHandler action="<action-id>" implementationClass="<EditorActionHandler FQN>" [id="<own-id>"] [order="<first|last|before|after <id>>"]/>`.
**Data Shape:** `action` is REQUIRED on every one of the 526 cluster declarations; `implementationClass` REQUIRED (enforced by `<with>`); `id` present on ~378 (needed only when another declaration anchors `order` against you or you anchor against others); `order` on ~297 (rider carries the densest chains: 206 handlers vs 160 py/ws).

### Decisive source
```xml
<!-- intellij.platform.debugger.impl.ui.jar:intellij.platform.debugger.impl.ui.xml:85-87 -->
<editorActionHandler action="EditorUp" implementationClass="com.intellij.xdebugger.impl.actions.handlers.UpHandler"
                     id="smart-step-into-up"/>
```
Debugger handlers wrap navigation actions (`EditorUp/Down/Left`) so stepping reuses caret-motion keys — interception keyed by ACTION ID, not by shortcut.

**Flow:** runtime builds one handler chain per action id → each declared handler wraps the previous "original" → execution walks wrappers outermost-first; `order` attributes sequence wrapper insertion relative to named sibling ids.
**Invariant:** an interceptor MUST delegate through to the wrapped original (the bean supplies the next handler) — a terminal handler that never delegates permanently disables the action for every later plugin. Wrong port: intercepting by copying the base action instead of declaring a handler for its id.
**Probe:** from install root: `for j in lib/*.jar; do unzip -p "$j" '*.xml' 2>/dev/null | grep -o '<editorActionHandler ' | wc -l; done | awk '{s+=$1} END{print s}'` → 154 (py), 154 (ws), 202 (rd). Declaration contract: `unzip -p lib/intellij.platform.ide.impl.jar META-INF/PlatformExtensionPoints.xml | grep -c 'implements="com.intellij.openapi.editor.actionSystem.EditorActionHandler"'` → 1.

## Get live surrounding code
**Retrieve:** manifest-only plane — the BM25 graph indexes no symbol for this EP (helpers-side noise only). Deterministic primitive:
```bash
unzip -p lib/intellij.platform.debugger.impl.ui.jar intellij.platform.debugger.impl.ui.xml | grep -n 'smart-step-into-up'
```
→ line 87 at pin PY-262.9437.214. Re-run after any build.txt advance before citing line numbers.

## Verdict
Adopt the per-action-id wrapper-chain model with explicit `order` anchoring; adapt the EP name to your registry's vocabulary; omit IntelliJ's `AnAction`/template-presentation machinery. Coverage caveat: counts are top-level-lib occurrences across the whole install; plugin-dir jars excluded. Boundary: menu placement of actions lives in action-menu-attachment-grammar; multi-block declaration mechanics in actions-multi-block-declarations; this capsule owns RUNTIME INTERCEPTION.
