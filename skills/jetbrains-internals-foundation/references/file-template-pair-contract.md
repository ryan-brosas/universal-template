<!-- capsule-v2 -->
# file-template-pair-contract — why does every shipped new-file template have an empty .ft AND a sibling .html?

**Source:** JetBrains installed distributions (proprietary), PyCharm `intellij.python.community.impl.jar` decisive instance. **Question:** How are new-file templates packaged, and what does the empty-body trap mean for a porter?

## fileTemplates/internal/<Name>.<ext>.ft + .html
**Path/Symbol:** `intellij.python.community.impl.jar:fileTemplates/internal/` — exactly 8 files = 4 templates × 2: `Python Script.py.ft`(+`.html`), `Python Stub.pyi.ft`(+`.html`), `Python Unit Test.py.ft`(+`.html`), `Setup Script.py.ft`(+`.html`).
**Signature:** `<Name>.<ext>.ft` = Velocity template (may be EMPTY bytes); `<Name>.<ext>.html` = description fragment for the template chooser.
**Data Shape:** `.py.ft` bodies are **zero-length** in the shipped install — the visible scaffolding comes from elsewhere (default code generation), so do NOT assume body content from the filename.

### Decisive source
```
$ unzip -l intellij.python.community.impl.jar | grep fileTemplates
fileTemplates/internal/Python Script.py.ft        (0 bytes)
fileTemplates/internal/Python Script.py.html
fileTemplates/internal/Python Stub.pyi.ft         (0 bytes)
fileTemplates/internal/Python Stub.pyi.html
fileTemplates/internal/Python Unit Test.py.ft     (0 bytes)
fileTemplates/internal/Python Unit Test.py.html
fileTemplates/internal/Setup Script.py.ft         (0 bytes)
fileTemplates/internal/Setup Script.py.html
```
```python
# probe output — raw read of Python Script.py.ft:
b''
```

**Flow:** user creates a file of a registered type → file-type → default-template lookup finds `fileTemplates/internal/<Name>.<ext>.ft` on the language module's classloader → chooser renders the `.html` description → body (empty here; user-editable copies live in the user config dir after first customization) is expanded through Velocity (`#parse`, `$NAME` variables when non-empty).
**Invariant:** the SHIPPED `.ft` may legitimately be empty because user-customized overrides live OUTSIDE the install in the config directory — internal templates are fallbacks, not sources of truth. Pair discipline: every `.ft` ships with its `.html` sibling; a missing html breaks only the chooser text.
**Probe:** `python3 -c "import zipfile;z=zipfile.ZipFile('pycharm/plugins/python-ce/lib/modules/intellij.python.community.impl.jar');n=sorted(x for x in z.namelist() if x.startswith('fileTemplates/'));print(len(n));print(repr(z.read('fileTemplates/internal/Python Script.py.ft')[:50]))"` → `8` + `b''`.
**Retrieve:** not symbol-indexed: `unzip -l <module-jar> | grep fileTemplates`.

## Verdict
Adopt: ship new-file scaffolds as (body-template, html-description) pairs under an `internal/` namespace that users can override externally. Adapt templating engine. Omit Velocity directives beyond noting emptiness. Caveat: emptiness is per-build observed behavior — if you need real scaffold content, port the USER-config override flow, not these bytes.
