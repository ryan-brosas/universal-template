<!-- capsule-v2 -->
# frontend-split-product-modules — how does the thin client know which plugins exist in the backend-only product?

**Source:** JetBrains installed distributions (proprietary), PyCharm `lib/frontend-split/` decisive instance; referenced by IJPL-A-306 comment in-file. **Question:** When UI runs in a separate frontend process, where is the reduced plugin/module list declared?

## product-modules.xml inside frontend-split.jar
**Path/Symbol:** `pycharm/lib/frontend-split/frontend-split.jar:META-INF/intellij.pycharm.frontend.split/product-modules.xml`.
**Signature:** `<product-modules> <include><from-module>…</from-module></include> <bundled-plugins><module>…</module>* </bundled-plugins> </product-modules>`.
**Data Shape:** PyCharm's file: 1 include + **7 bundled plugin modules** (customization, python community plugin, python plugin, toml, notebooks, jupyter, jupyter-colab) — versus 114 full-install plugins. The jar contains ONLY this descriptor + an `__index__` marker: pure metadata artifact.

### Decisive source
```xml
<!-- Specifies bundled plugins and additional modules in the core plugin for the frontend variant of PyCharm (JetBrains Client),
     see IJPL-A-306 for details -->
<product-modules>
  <include>
    <from-module>intellij.frontend.split.customization</from-module>
  </include>
  <bundled-plugins>
    <module>intellij.pycharm.frontend.split.customization</module>
    <module>intellij.python.community.plugin</module>
    <module>intellij.python.plugin</module>
    <module>intellij.toml</module>
    <module>intellij.notebooks.plugin</module>
    <module>intellij.jupyter.plugin</module>
    <module>intellij.jupyter.py.colab.plugin</module>
  </bundled-plugins>
</product-modules>
```

**Flow:** thin-client persona boots (`-Dintellij.platform.root.module=intellij.pycharm.frontend.split`, product.mode=frontend) → loader reads this product-modules.xml → include pulls the customization module first → bundled-plugins list becomes the ONLY plugins the frontend loads; everything else stays in the backend process and is reached over RPC.
**Invariant:** the frontend list is a strict SUBSET expressed as module names (not plugin ids) — a porter adding a frontend capability must add it HERE plus the customization module, or it silently exists only backend-side. The `__index__` entry marks the jar as index-only (no code).
**Probe:** `python3 -c "import zipfile;z=zipfile.ZipFile('pycharm/lib/frontend-split/frontend-split.jar');print(z.namelist());print(z.read('META-INF/intellij.pycharm.frontend.split/product-modules.xml').decode().count('<module>'))"` → 2 entries listed, `7`. Companion jar `frontend-split-customization.jar` carries the customization module.
**Retrieve:** not symbol-indexed: `unzip -l pycharm/lib/frontend-split/frontend-split.jar`.

## Verdict
Adopt: when splitting a monolith into front/back processes, declare the frontend's visible surface as an explicit include+allowlist metadata artifact instead of duplicating manifests — keeps one source of truth with a filtered view. Adapt module-name vocabulary. Omit IntelliJ loader specifics. Caveat: counts are per-build; re-census on any build bump.
