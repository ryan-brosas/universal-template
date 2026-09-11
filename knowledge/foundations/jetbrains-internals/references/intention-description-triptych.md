<!-- capsule-v2 -->
# intention-description-triptych — what three files ship per intention action so the IDE can show before/after?

**Source:** JetBrains installed distributions (proprietary), WebStorm `intellij.javascript.backend.jar` decisive instance (213 intentions). **Question:** How are intention actions documented as executable before/after pairs instead of prose?

## intentionDescriptions/<IntentionName>/{description.html, before.js.template, after.js.template}
**Path/Symbol:** `<module-jar>:intentionDescriptions/ES6AddExportDefaultIntention/description.html` + `before.js.template` + `after.js.template`.
**Signature:** directory-per-intention; `.template` files = raw code samples shown in the settings diff view; `description.html` = one-paragraph rationale.
**Data Shape:** WebStorm javascript backend jar: 210 `inspectionDescriptions` + **213 intention dirs × ~2–3 files ≈ 550+ entries**; cluster-wide inten counts 3.9k–4.8k per full install (see inspection-description-catalog census). PyCharm python plane carries 10 intention htmls in psi.impl + more across community.impl.

### Decisive source
```
intentionDescriptions/ES6AddExportDefaultIntention/
├── after.js.template      # export default function foo() {\n}
├── before.js.template     # function foo() {\n}
└── description.html       # <html><body><p>Adds <code>export default</code>…</p></body></html>
```
```js
// after.js.template — verbatim first lines:
export default function foo() {
}
```

**Flow:** intention registered via compound-tag `intentionAction` XML (see intention-action-metadata) with `className="ES6AddExportDefaultIntention"` → settings page ("Intentions" family) locates `intentionDescriptions/<className>/description.html` and renders before.template→after.template as a live diff preview → runtime invocation executes the class; templates are documentation-only.
**Invariant:** the DIRECTORY name must equal the intention's `className`; the pair of `.template` files must be same-language and minimal — they are rendered verbatim with no variable substitution. A porter copying only description.html loses the diff preview (the actual teaching surface).
**Probe:** `python3 -c "import zipfile;z=zipfile.ZipFile('webstorm/plugins/javascript-plugin/lib/modules/intellij.javascript.backend.jar');n=[x for x in z.namelist() if x.startswith('intentionDescriptions/')];print(len(n));print(z.read('intentionDescriptions/ES6AddExportDefaultIntention/after.js.template').decode())"` → 213-ish entries + the two-line export-default snippet above.
**Retrieve:** not symbol-indexed: `unzip -l webstorm/plugins/javascript-plugin/lib/modules/intellij.javascript.backend.jar | grep intentionDescriptions | head`.

## Verdict
Adopt: document behavior-changing quick-fixes as (prose, before-sample, after-sample) triptychs shipped beside the implementation — cheaper and more truthful than screenshots. Adapt extension/language to host. Omit IntelliJ rendering pipeline. Caveat: template languages vary per plugin (.java.template, .py.template); glob by `*.template`, not a fixed suffix.
