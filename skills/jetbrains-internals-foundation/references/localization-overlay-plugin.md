<!-- capsule-v2 -->
# localization-overlay-plugin — how do 3,988 localized inspection docs ride WITHOUT forking the base product?

**Source:** JetBrains installed distributions (proprietary), Rider `plugins/localization-ja/lib/localization-ja.jar` decisive instance (7556 entries). **Question:** How is a full UI language shipped as a pure overlay that never touches a code jar?

## localization-<lang>.jar as resource mirror
**Path/Symbol:** `rider/plugins/localization-ja/lib/localization-ja.jar` — top-level dirs: `inspectionDescriptions/`=3,988 · `messages/`=1,429 · `intentionDescriptions/`=1,225 · `fileTemplates/`=584 · `postfixTemplates/`=322 (+ `bundle/` 3).
**Signature:** SAME paths and file names as the English resources inside code jars (`messages/Jinja2Bundle.properties`, `inspectionDescriptions/XxxInspection.html`, `intentionDescriptions/<Name>/description.html`, `postfixTemplates/<Name>/description.html`) but with translated CONTENT; classpath ordering makes the overlay win lookup.
**Data Shape:** zero .class files; zero META-INF/plugin.xml beyond module marker (2 entries); Japanese prose confirmed in-file.

### Decisive source
```html
<!-- postfixTemplates/TableTemplatePostfixCompletion/description.html (ja overlay) -->
<html>
<body>JS 埋め込みコンテンツ内の iterable オブジェクトを検出し、定義されたテーブルテンプレートのいずれかに展開します。</body>
</html>
```
```
messages/Jinja2Bundle.properties      # same key set as base bundle, ja values
inspectionDescriptions/…/Xxx.html     # 3,988 mirrored docs
```

**Flow:** plugin ships as one of rider's bundled plugins → platform prepends its jar to the resource-search order → every bundle/doc lookup finds the localized twin first; missing keys fall through to English in the code jar → no rebuild or patching of any base artifact.
**Invariant:** the overlay MUST mirror paths exactly (dir + filename) — it is keyed by convention, not by an index file; adding a new inspection to the base without an overlay entry degrades silently to English rather than erroring. Sibling language packs exist (`localization-ko`, `localization-zh` in rider's plugins/).
**Probe:** `python3 -c "import zipfile,collections;z=zipfile.ZipFile('rider/plugins/localization-ja/lib/localization-ja.jar');c=collections.Counter(n.split('/')[0] for n in z.namelist());print(dict(c.most_common(5)))"` → `{'inspectionDescriptions': 3988, 'messages': 1429, 'intentionDescriptions': 1225, 'fileTemplates': 584, 'postfixTemplates': 322}`.
**Retrieve:** not symbol-indexed: `unzip -l rider/plugins/localization-ja/lib/localization-ja.jar | head -30`.

## Verdict
Adopt: ship translations as path-mirroring pure-resource overlays that shadow by classpath order instead of localizing inside code artifacts — keeps code jars byte-stable across languages. Adapt lookup precedence to host classloading. Omit JetBrains fallback internals. Caveat: coverage lags base (1,225 of ~4.5k intentions here); treat overlays as best-effort mirrors, never as the canonical doc source.
