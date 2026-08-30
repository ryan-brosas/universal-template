<!-- capsule-v2 -->
# tips-and-help-surface — where do per-product tip-of-the-day docs and key reference cards ride?

**Source:** JetBrains installed distributions (proprietary), PyCharm decisive instances. **Question:** How is user-education content partitioned across plugins and the install root?

## plugins/<x>/lib/tips-<product>.jar + help/*.pdf
**Path/Symbol:** `pycharm/plugins/pycharm-pro-customization/lib/tips-pycharm-pro.jar:tips/GoToInspection.html`, `tips/ConsolesCodeCompletion.html`; `plugins/DatabaseTools/lib/tips-database-plugin.jar:tips/{DBRunQuery,DBConsole}.html`; `help/ReferenceCard.pdf` + `ReferenceCardForMac.pdf` at install root.
**Signature:** `tips/<TipName>.html` — one self-contained HTML page per tip, filename = tip id; product-specific tip jars named `tips-<product|feature>.jar` so the SAME plugin can ship different tips per IDE.
**Data Shape:** colors plane rides similarly per-plugin: `sh-plugin/lib/intellij.sh.core.jar:colors/{ShDarcula,ShDefault}.xml`; `cwm-plugin/.../colors/{dark,light}_attributes.xml`.

### Decisive source
```
$ unzip -l pycharm/plugins/DatabaseTools/lib/tips-database-plugin.jar
tips/DBConsole.html
tips/DBRunQuery.html
$ ls pycharm/help
ReferenceCardForMac.pdf  ReferenceCard.pdf
```

**Flow:** tip-of-the-day service enumerates `tips/*.html` across the plugin classpath → picks by product filter + shown-history (user config) → renders HTML directly; the PDF cards are static assets referenced by Help menu actions.
**Invariant:** tips are keyed by FILENAME and grouped per feature-plugin, not centralized — a plugin contributes education content by simply adding a jar; no registry file lists them. Product variants are separate jars (`tips-pycharm-pro`), never conditional content inside one file.
**Probe:** `python3 -c "import zipfile;print(zipfile.ZipFile('pycharm/plugins/DatabaseTools/lib/tips-database-plugin.jar').namelist())"` → the two tips entries above.
**Retrieve:** not symbol-indexed: `find <ide>/plugins -name 'tips-*.jar' | head`.

## Verdict
Adopt: education/onboarding docs as filename-keyed HTML slabs packaged beside their feature, with per-product variants as parallel jars. Adapt naming. Omit JetBrains' history-tracking service. Caveat: minor surface — mine only when porting an onboarding pipeline; counts are small and volatile.
