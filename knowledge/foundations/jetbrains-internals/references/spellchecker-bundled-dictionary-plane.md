<!-- capsule-v2 -->
# Bundled spellchecker dictionary plane — where do domain words come from and how are they scoped?

**Source:** JetBrains IDE distributions (proprietary distribution; platform XML headers marked Apache-2.0); study/reference use only; Codebase Memory `jetbrains-pycharm`. **Question:** How does a spellchecker ship per-language-domain vocabularies without one giant dictionary, and what wiring (EP + strategy + provider) binds a dictionary to a language?

## Connected graph-selected seam
**Path/Symbol:** `lib/intellij.spellchecker.jar` → `com/intellij/spellchecker/{jetbrains.dic,names.dic}`; `plugins/javascript-plugin/lib/modules/intellij.javascript.backend.spellchecker.jar` → 27 `.dic` files + `intellij.javascript.backend.spellchecker.xml`.
**Signature:** `<spellchecker.support language="XML" implementationClass="com.intellij.spellchecker.xml.XmlSpellcheckingStrategy" id="xml"/>`; EP `JavaScript.spellcheckerProvider` interface=`...JSSpellcheckerProvider` dynamic=true; `<spellchecker.bundledDictionaryProvider implementation="...JSDictionaryProvider"/>`.
**Data Shape:** `.dic` = plain newline word list, possessives expanded inline (`accused`, `accused's`, `accuseds`). Base jar carries 447-word `jetbrains.dic` + 23-word `names.dic`. Domain jars carry per-ecosystem lists: JS backend = 27 npm-flavored (`@angular.dic`, `@types.dic`, `_javascript.dic` — note leading-@/_ filename escapes), python = 8 ecosystem dics (django/pytest/sqlalchemy/tox/acronyms/logging), ruby backend = **79 gem-named dics** (RedCloth/actionmailer/activerecord…), plus per-plugin singles (swagger.dic, grpc.dic, docker.dic, vue.dic).

### Decisive source
```xml
<extensions defaultExtensionNs="com.intellij">
    <spellchecker.support language="JavaScript"
                          implementationClass="...JSSpellcheckingStrategy"/>
    <spellchecker.support language="JSON" order="first"
                          implementationClass="...PackageJsonSpellcheckingStrategy"/>
    <spellchecker.bundledDictionaryProvider implementation="...JSDictionaryProvider"/>
</extensions>
<extensions defaultExtensionNs="JavaScript">
    <spellcheckerProvider implementation="...JSDirectiveCommentSpellcheckerProvider"/>
</extensions>
```

**Flow:** base spellchecker module owns the generic wordlists → each language module ships a `spellchecker.support` strategy (tokenizes only identifiers/strings/comments) PLUS a bundled-dictionary provider that resolves its `.dic` classloader-relative → `order="first"` lets package.json override the JSON strategy.
**Invariant:** dictionaries are data, strategies are code; the provider indirection means adding vocabulary never touches the tokenizer. Filename characters that break classpath lookup get escaped (`@angular.dic`, `_javascript.dic`) — a porter must keep that mapping stable.
**Probe:** `unzip -p lib/intellij.spellchecker.jar com/intellij/spellchecker/jetbrains.dic | wc -l` → `447`; `unzip -l plugins/javascript-plugin/lib/modules/intellij.javascript.backend.spellchecker.jar | grep -c '\.dic'` → `27`.
**Coverage caveat:** resource-plane capsule; cited via direct jar reads. The indexed code twin is the XML-strategy class in `intellij.spellchecker.xml.jar` (see graph retrieval).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "spellchecking strategy xml html tokenizer", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: per-language-module dictionary ownership, provider-resolved classloader-relative wordlists, escaped-filename convention, strategy+dictionary split. Adapt wordlist formats to your host spellchecker. Omit the actual vocabularies. Cluster census: pycharm 44 dics / rubymine 114 / datagrip 3 — volume follows language surface.
