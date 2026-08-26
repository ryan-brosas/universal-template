<!-- capsule-v2 -->
# required-if-available-module-gating — when must a content module load "only if a named platform module exists"?

**Source:** JetBrains installed distributions (proprietary), RustRover decisive instances (9 bundled plugins). **Question:** What loading rule do you use for modules that are mandatory on hosts that HAVE a capability and silently absent elsewhere — without making them `optional`?

## `<module ... required-if-available="<module-fqn>">` hybrid gate
**Path/Symbol:** `rustrover/plugins/intellij-rust/lib/intellij-rust.jar:META-INF/plugin.xml` → `<module name="intellij.rustrover.core" required-if-available="intellij.platform.backend">`; same attribute in `plugins/rustrover-customization-plugin/.../plugin.xml` (`intellij.rustrover.customization.backend`), `javascript-debugger` (6 uses), `json`, `css-plugin`, `javascript-plugin`, `jcef-plugin`, `platform-testRunner-plugin`, `vcs-git`.
**Signature:** attribute value = a MODULE name (not plugin id) resolved against the runtime module repository; presence → module loads like `required`; absence → module is skipped without error, like an unmet optional.
**Data Shape:** census in this install: 20 occurrences across 9 bundled plugins — javascript-debugger 6, intellij-rust 4 (core, nativeDebug, frontend→intellij.platform.frontend, frontend.split→intellij.platform.frontend.split), json 2, javascript-plugin 2, css-plugin 2, jcef 1, platform-testRunner 1, rustrover-customization 1, vcs-git 1. The dominant use: gating `*.backend` / frontend-split twins on `intellij.platform.backend` / `intellij.platform.frontend(.split)` so one descriptor serves monolith AND split-frontend boots.

### Decisive source
```xml
<!-- intellij-rust.jar:META-INF/plugin.xml -->
<module name="intellij.rustrover.common" loading="embedded">…</module>
<module name="intellij.rustrover.core" required-if-available="intellij.platform.backend">…</module>
<module name="intellij.rustrover.frontend" required-if-available="intellij.platform.frontend">…</module>
<module name="intellij.rustrover.frontend.split" required-if-available="intellij.platform.frontend.split">…</module>
<!-- rustrover-customization-plugin.jar -->
<module name="intellij.rustrover.customization.backend" required-if-available="intellij.platform.backend"><![CDATA[<idea-plugin>
  <dependencies><module name="intellij.platform.backend" /><module name="intellij.platform.whatsNew" /></dependencies>…]]></module>
```

**Flow:** descriptor parse → for each content module: evaluate loading= first (embedded = merge into parent classpath), then required-if-available → look up the named module in the runtime repo (modules/module-descriptors.dat world) → found: treat as required dependency and load; missing: drop this content module only, siblings unaffected.
**Invariant:** the gate keys on MODULE existence, not plugin id, and never fails the host — it is the join point that lets ONE descriptor ship both halves of a frontend/backend split while each boot persona sees exactly its half. Do not confuse with `loading="optional"` (a property of THIS module's load style) or `<depends optional="true">` (optional PLUGIN dep at top level).
**Probe:** `python3 - <<'EOF'
import zipfile,glob
hits={}
for j in glob.glob('rustrover/plugins/*/lib/*.jar'):
    try: x=zipfile.ZipFile(j).read('META-INF/plugin.xml').decode('utf-8','replace')
    except Exception: continue
    n=x.count('required-if-available')
    if n: hits[j.split('/plugins/')[1].split('/')[0]]=n
print(sum(hits.values()), sorted(hits.items()))
EOF` → `20 [('css-plugin',2),('intellij-rust',4),('javascript-debugger',6),('javascript-plugin',2),('jcef-plugin',1),('json',2),('platform-testRunner-plugin',1),('rustrover-customization-plugin',1),('vcs-git',1)]`.
**Retrieve:** not symbol-indexed (jar XML); graph confirms the owning plugin dirs exist:
```ts
await mcp.codebase_memory.check_index_coverage({ project: "jetbrains-rustrover", paths: ["plugins/rustrover-customization-plugin/lib/rustrover-customization-plugin.jar"] });
```

## Verdict
Adopt: required-if-available as the split-boot join rule — capability-presence-gated mandatory modules. Adapt the attribute name to your manifest grammar; keep the two-sided semantics (load-as-required iff present, else silent skip). Omit: JetBrains' platform.backend/frontend module names. Caveat: semantics derived from descriptor grammar + usage census of one 2026.2.1 install; runtime boot behavior not traced (jar-only code).
