<!-- capsule-v2 -->
# live-template-set-contract — how do expandable snippets declare variables, defaults, and applicability contexts?

**Source:** JetBrains installed distributions (proprietary), sh-plugin `intellij.sh.backend.jar` decisive instance; grpc plugin `intellij.httpClient.grpc.jar` second instance. **Question:** How is a live-template (typed abbreviation → expansion) expressed as data so new snippet packs need no code?

## liveTemplates/<Set>.xml
**Path/Symbol:** `pycharm/plugins/sh-plugin/lib/modules/intellij.sh.backend.jar:liveTemplates/ShellScript.xml` (+ `ShellScriptArray.xml`, hidden variants); `intellij.httpClient.grpc.jar:liveTemplates/grpcRequest.xml`.
**Signature:** `<templateSet group="..."> <template name="fori" value="..." resource-bundle="messages.ShBundle" key="sh.livetemplate.description.fori" description="..." toReformat="true" toShortenFQNames="false"> <variable name="INDEX" expression="" defaultValue="&quot;i&quot;" alwaysStopAt="true"/> <context><option name="SHELL_SCRIPT" value="true"/><option name="OTHER" value="false"/></context> </template>* </templateSet>`.
**Data Shape:** `$NAME$` placeholders in `value`; `$END$` = final caret stop; `$SELECTION$` = wrap-selection templates; per-variable `expression` (predefined functions), `defaultValue`, `alwaysStopAt`.

### Decisive source
```xml
<templateSet group="Shell Script">
  <template name="fori"
            value="for $INDEX$ in $LOOP_ITEMS$ ; do&#10;    $END$$SELECTION$&#10;done"
            resource-bundle="messages.ShBundle" key="sh.livetemplate.description.fori"
            description="For loop in list" toReformat="true" toShortenFQNames="false">
    <variable name="INDEX" expression="" defaultValue="&quot;i&quot;" alwaysStopAt="true"/>
    <variable name="LOOP_ITEMS" expression="" defaultValue="&quot;{1..5}&quot;" alwaysStopAt="true"/>
    <context>
      <option name="SHELL_SCRIPT" value="true"/>
      <option name="OTHER" value="false"/>
    </context>
  </template>
```

**Flow:** user types `fori`+Tab inside a context whose option flag matches (`SHELL_SCRIPT=true`) → template expands with numbered variable stops in declaration order → each stop accepts input or falls to `defaultValue`; descriptions are i18n keys into the module's message bundle (never inline user-facing text).
**Invariant:** the `<context>` option allowlist is the ONLY applicability gate — a template without a matching context option is dead data; `description=` duplicates the bundle value here but `key`+`resource-bundle` are what i18n resolution uses. Hidden sets (`*Hidden.xml`) carry templates suppressed from the settings UI.
**Probe:** `python3 -c "import zipfile;z=zipfile.ZipFile('pycharm/plugins/sh-plugin/lib/modules/intellij.sh.backend.jar');print([n for n in z.namelist() if 'liveTemplates' in n]);print(z.read('liveTemplates/ShellScript.xml').decode()[:400])"` → 3 files + the fori block above.
**Retrieve:** not symbol-indexed: `unzip -l <module-jar> | grep liveTemplates`.

## Verdict
Adopt: snippets as declarative sets — placeholder grammar, variable defaults, and context flags in XML, descriptions via bundle keys. Adapt placeholder syntax to your editor. Omit predefined-expression function library. Caveat: template sets are scattered across language plugins (grep per jar); there is no install-wide index file.
