<!-- capsule-v2 -->
# mc:Ignorable preprocessing — why does schema-valid markup with extension namespaces pass the XSD gate?

**Source:** anthropics/skills Apache-2.0/source-available `main@3b3fad96`; Codebase Memory `skills`. **Question:** OOXML documents legally carry `mc:Ignorable` extension namespaces that the strict ISO-29500 XSDs reject — how does the validator keep them from failing your edit?

## Three-stage strip before lxml validation, main parts only
**Path/Symbol:** `skills/docx/scripts/office/validators/base.py` (`_preprocess_for_mc_ignorable` :767-773; `_clean_ignorable_namespaces` :728-746; `_remove_ignorable_elements` :748-765; `OOXML_NAMESPACES` :88-104; applied in `_validate_single_file_xsd` :786-799).
**Signature:** `xml_doc = self._preprocess_for_mc_ignorable(xml_doc)` → (main folders only) `xml_doc = self._clean_ignorable_namespaces(xml_doc)` → subclass `_preprocess_for_schema`.
**Data Shape:** allow-list `OOXML_NAMESPACES` = 14 canonical officeDocument/DrawingML/WordprocessingML/PresentationML/SpreadsheetML/math/sharedTypes/xml namespaces; anything outside is ignorable.

### Decisive source
```python
# :793-797 — the strip applies ONLY to main content parts:
if (relative_path.parts
        and relative_path.parts[0] in self.MAIN_CONTENT_FOLDERS):
    xml_doc = self._clean_ignorable_namespaces(xml_doc)
# _remove_template_tags_from_text_nodes (:842-871) SKIPS w:t entirely:
if tag_str.endswith("}t") or tag_str == "t":
    continue   # {{placeholders}} in visible text are CONTENT, not scaffolding
```
Order inside `_validate_single_file_xsd`: template-tag removal → root-attr drop (`mc:Ignorable`) → namespace strip (main parts) → subclass hook → `schema.validate`.

**Flow:** every attribute in a non-allow-listed namespace is deleted, then whole elements whose tag namespace is outside the list are removed recursively — so `w14:paraId`, `w16cid:durableId`, `mc:AlternateContent` children etc. never reach the XSD. Subclasses may further mutate via `_preprocess_for_schema` (pptx uses it to repair child order).
**Invariant:** this runs on a THROWAWAY copy (round-tripped through tostring/fromstring), never on disk bytes — porters must not "optimize" it into an in-place rewrite of user files; and template tags in `<w:t>` must survive because they are document text.
**Probe:** `grep -n "_clean_ignorable_namespaces\|endswith(\"}t\")" validators/base.py | head -4` shows the gated call at :793-797 and the w:t skip at :865-866 (executed @3b3fad96, both present).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_code({ project: "skills", pattern: "_clean_ignorable_namespaces", limit: 5 });
```

## Verdict
Adopt the pattern: validate a sanitized COPY against strict XSDs using a closed namespace allow-list, preserving original bytes on disk and visible text nodes. Adapt the allow-list to whichever OOXML namespaces your host emits. Omit template-tag handling if your pipeline has no `{{}}` scaffold stage. Coverage caveat: no upstream tests; behavior verified by source read + grep probe.
