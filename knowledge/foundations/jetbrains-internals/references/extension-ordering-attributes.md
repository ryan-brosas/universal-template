<!-- capsule-v2 -->
# Extension ordering attributes — how does declarative registration sequence itself without code?

**Source:** JetBrains IDE distributions (proprietary distribution; study/reference use only); direct jar reads; Codebase Memory `jetbrains-pycharm`. **Question:** When multiple plugins contribute to one extension point, what XML vocabulary controls their execution/visual order?

## order= vocabulary
**Path/Symbol:** platform + product `META-INF/*.xml` extension tags, e.g. `lib/intellij.platform.vcs.impl.jar!META-INF/VcsExtensions.xml`, `lib/intellij.platform.externalSystem.impl.jar!META-INF/ExternalSystemExtensions.xml`.
**Signature:** `order="first" | order="last" | order="after <id>" | order="before <id>"` — an OPTIONAL attribute on any EP contribution.
**Data Shape:** VcsExtensions.xml alone shows the full grammar: `order="last"` (externalSystemViewContributor default slot), `order="first"`/`"last"` pairs bracketing ShowDiffAction providers, `order="after DefaultFloatingToolbarProvider"` and `order="after VCS.DefaultIgnoredFileProvider"` anchoring to a NAMED sibling id. Unspecified = registration order (jar/plugin load order) — never rely on it.

### Decisive source
```xml
<editorFloatingToolbarProvider
      id="ExternalSystem.ProjectRefreshFloatingProvider"
      order="after DefaultFloatingToolbarProvider" .../>
<diff.actions.ShowDiffAction.ExtensionProvider implementation="...ShowEditorDiffPreviewActionProvider" order="first"/>
<diff.actions.ShowDiffAction.ExtensionProvider implementation="...ShowDiffAction" order="last"/>
<ignoredFileProvider id="VCS.DefaultIgnoredFileProvider" .../>
<ignoredFileProvider ... order="after VCS.DefaultIgnoredFileProvider"/>
<modelScopeItemPresenter ... id="vcs_scope" order="after module_scope" />
```

**Flow:** container collects all EP contributions → sorts by explicit order constraints into a total order (named-id anchors resolve against other contributions' `id=` attrs) → iteration order becomes behavior (first handler wins, last listener closes, UI appends in sequence). The `id`+`order="after <id>"` pair is the ONLY way a later-shipped plugin inserts itself mid-sequence.
**Invariant:** order anchors reference CONTRIBUTION IDS, not class names — if the anchor id is absent (plugin disabled), the constraint degrades to unspecified position, not an error. Wrong port: anchoring to a class FQN or assuming first-registration wins.
**Probe:** `unzip -p pycharm/lib/intellij.platform.vcs.impl.jar META-INF/VcsExtensions.xml | grep -oE 'order="(first|last|after [^"]*")' | sort | uniq -c` → shows all four forms present in one file.
**Coverage caveat:** resource-plane capsule; cited via direct jar extraction.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "extension point order sorting comparator loadingOrder", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: first/last/before/after-with-named-anchor ordering grammar for ANY declarative registry where multiple contributors race; keep anchors on stable public ids. Adapt tie-breaking for cycles. Omit IntelliJ's specific sorter implementation. Complements action-override-replacement (replacement is order's extreme case).
