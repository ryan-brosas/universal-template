<!-- capsule-v2 -->
# Shipped options-data plane — where do default settings values actually live in an installed IDE?

**Source:** JetBrains IDE distributions (proprietary distribution; platform XML headers Apache-2.0) — study/reference use only; Codebase Memory `jetbrains-pycharm` (install-tree, not git). **Question:** If you port "IDE defaults ship as `options/*.xml` under a config dir", what does the shipped artifact ACTUALLY contain, and where would you put your own shipped defaults?

## Connected graph-selected seam
**Path/Symbol:** jar-internal paths matching `(^|/)options/*` across ALL jars of pycharm/webstorm/rider/goland (LC_ALL=C unzip -l census).
**Signature:** n/a (resource plane — no callable surface).
**Data Shape:** pycharm: 1,584 `options/` entries — 100% `.class` compiled Kotlin/Java under `com/intellij/**/options/**` (UI panels and option-descriptor classes like `options/editor/EditorTabsConfigurable.class`, `options/codeStyle/cache/CodeStyleCachedValueProvider.class`). Non-class data files found cluster-wide outside qodana.jar: exactly FIVE (`colors/ShDarcula.xml`, `colors/ShDefault.xml`, `colors/dark_attributes.xml`, `colors/light_attributes.xml`, plus toml's demo text at its OWN package path). webstorm/rider/goland: only qodana's vendored maven `options/pom.xml`+`pom.properties`. NO shipped `options/*.xml` settings data exists anywhere.

### Decisive source
```
$ cd <install root>
$ find lib plugins -name '*.jar' | while read j; do
    unzip -l "$j" | grep -aoE '(inspectionProfiles|options|colors|codeStyles|scopes)/[^ "<>]+'
      | sed "s|^|$j |"; done | grep -v '\.class' | wc -l
5        # pycharm: the five color-scheme/demo files above — zero options XML
1584     # total options/ entries, all .class
```

**Flow:** build time bakes defaults into code (`@Property`-annotated fields, `OptionDescriptor`s) → user config dir receives XML ONLY when the user changes something → installs ship ZERO declarative defaults. The `defaults/` and `options/` directories of a RUNNING profile are runtime artifacts, not install payloads.
**Invariant:** any port that expects to edit "the shipped options XML" is porting a fiction — defaults are code constants; shipping your own defaults means shipping a class or a resource YOUR loader reads.
**Probe:** `unzip -l lib/intellij.platform.ide.impl.jar | grep 'options/' | head -3` → all three lines end `.class`; then `find lib plugins -name '*.jar' | while read j; do unzip -l "$j" | grep -aqE '^ *[0-9]+ .* options/[A-Za-z0-9_.$-]+\.xml$' && echo "$j"; done | wc -l` from the install root prints `0`.
**Coverage caveat:** resource plane inside jars — NOT symbol-indexed; deterministic unzip probes are the retrieval primitive (BM25 search_graph returns helpers-side noise on these tokens).

## Get live surrounding code
**Retrieve:** graph does not index jar resources. Deterministic probes above ARE the retrieval; for the code side of option descriptors use:
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "configurable OptionDescriptor advanced settings", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: "shipped defaults = code, not XML" as a design contract (compile your defaults; keep user overrides external). Adapt: your host's config-file discovery. Omit: IntelliJ's PersistentStateComponent machinery itself. Erratum vs older mental model AND vs pass-4's `.icls/.uitheme` zero-hit record: this closes the question corpus-wide — the entire `options/` namespace inside shipped jars is CLASSES, not configuration data.
