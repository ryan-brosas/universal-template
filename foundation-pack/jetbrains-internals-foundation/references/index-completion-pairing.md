<!-- capsule-v2 -->
# Index-backed completion pairing — fileBasedIndex + completion.contributor twins

**Source:** JetBrains IDE installed build `PyCharm 262.9437.214` (PRO module `plugins/python/lib/modules/intellij.python.jar:intellij.python.xml:103-113,132,138`; community `plugins/python-ce/lib/modules/intellij.python.community.impl.jar`); Codebase Memory `jetbrains-pycharm`. **Question:** How does a plugin serve completion of values that live in OTHER files (template variables, route endpoints) without parsing the whole project on every keystroke?

## Flask stub-index family (5 index/contributor pairs)
**Path/Symbol:** `intellij.python.xml` Flask region `:95-119`; FastAPI endpoint pair `:129-138`.
**Signature:** `<fileBasedIndex implementation="<...Index extends FileBasedIndexExtension>"/>` paired with `<completion.contributor language="Python" implementationClass="<...Contributor>"/>`; variant for symbol search: `<stubIndex implementation="<...StubKeyIndex>"/>` (:146).
**Data Shape:** the index extension declares its key/value types and input-filter; the contributor queries it during completion. The five Flask indexes: `FlaskSessionKeyIndex`(:105), `FlaskRequestFormKeyIndex`(:107), `FlaskGAttributesIndex`(:110), `FlaskTemplateVariableIndex`(:112), `FlaskRenderTemplateCallersIndex`(:113) — each with a same-prefix contributor (:104,106,108-109,111); endpoint routers: `FastApiRouterIndex`(:132)/`FlaskRouterIndex`(:138).

### Decisive source
```xml
<completion.contributor language="Python" implementationClass="com.intellij.python.pro.flask.completion.FlaskSessionKeyCompletionContributor"/>
<fileBasedIndex implementation="com.intellij.python.pro.flask.stubs.FlaskSessionKeyIndex"/>
```
(contributor declared IMMEDIATELY BEFORE its index in source order; naming pairs `<Feature><Kind>CompletionContributor` with `<Feature><Kind>Index`.)

**Flow:** background indexing pass builds per-file maps → user types inside a Jinja/Python context → contributor intercepts, queries the prebuilt index for candidate keys → suggestions return without touching unrelated files.
**Invariant:** the contributor is a VIEW over an index that must be separately registered; registering only the contributor yields empty completions, only the index yields no UI. Wrong port: building completion by eager project scan at keystroke time (the thing this pairing exists to avoid).
**Probe:** deterministic: `unzip -p plugins/python/lib/modules/intellij.python.jar intellij.python.xml | grep -cE 'fileBasedIndex implementation=.*flask\.stubs'` → 5; `| grep -c 'flask.completion.Flask'` → 6.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "pydev console completion option", limit: 10, fields: ["signature", "name", "file"] });
```
(index extensions are compiled jar classes; helper-side completion plumbing IS indexed, e.g. `_pydev_bundle/pydev_console_utils.py:42-45`.)

## Verdict
Adopt declare-index-then-query-from-contributor as the pattern for cross-file value completion; adapt index key/value typing to your host's indexer; omit IntelliJ's stub-index serialization formats. Coverage caveat: manifest read from jar.
