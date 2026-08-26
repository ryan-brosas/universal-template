<!-- capsule-v2 -->
# Baseline-diff XSD gating — why does a template-derived file pass with defects the schema rejects?

**Source:** anthropics/skills Apache-2.0/source-available `main@3b3fad96`; Codebase Memory `skills`. **Question:** when validating an edited OOXML package against the ISO-29500 XSDs, which errors are YOURS and which came with the template?

## New-errors-vs-original-baseline, position-free
**Path/Symbol:** `skills/docx/scripts/office/validators/base.py` (`BaseSchemaValidator.validate_against_xsd` :661-708; `validate_file_against_xsd` :623-659; `_validate_single_file_xsd` :778-810; `_get_original_file_errors` :812-840).
**Signature:** `validate_file_against_xsd(xml_file, verbose=False) -> (True|False|None, set[str])`; `None` = no schema mapped for that part.
**Data Shape:** errors compared as `set[str]` of lxml message strings — **position-free**: identical defects at different lines cancel out.

### Decisive source
```python
# validate.py:99 — original_file presence flips the whole gate:
family = OOXML_FAMILY.get((original_file or path).suffix.lower())
# base.py:636-639 — the baseline subtraction:
original_errors = self._get_original_file_errors(xml_file)
assert current_errors is not None
new_errors = current_errors - original_errors
```
The original is re-unpacked per part (`safe_extract` into a temp dir), validated with the SAME schema path, and its error strings become the subtracted baseline. `IGNORED_VALIDATION_ERRORS = ["hyphenationZone", "purl.org/dc/terms"]` (:26-29) filters known-noisy messages from the remainder.

**Flow:** parse part → strip template tags outside text nodes → drop root `mc:Ignorable` attr → for MAIN_CONTENT_FOLDERS parts, remove attrs/elements in non-OOXML namespaces (`_clean_ignorable_namespaces`) → subclass hook `_preprocess_for_schema` → XSD validate → if invalid, subtract original's error set → report only survivors.
**Invariant:** without `--original`, ANY XSD violation fails the run (rc=1); template-inherited violations pass ONLY because they exist identically in both error sets. A "fix" that merely relocates an inherited defect still passes — position-free comparison is deliberate. MASKING HAZARD (pass-7 refinf audit [DONE:332], executed live): lxml XSD validation reports only the FIRST unexpected element at a position — a NEW defect placed AFTER an identical shared bogus element in both files produces the SAME single error string in both sets, cancels in subtraction, and passes rc=0 (verified: original `<w:bogus/>` vs new `<w:bogus/><w:bogus2/>` both yield only the `{...}bogus` not-expected error; residual = ∅). Baseline-diff gating is therefore sound for TEMPLATE-INHERITED noise but NOT a general defect-finder for structurally-broken documents; pair it with structural checks when the baseline itself fails its XSD.
**Probe (audit addendum):** unpack original `<w:bogus/>` and candidate `<w:bogus/><w:bogus2/>` docx, run `_validate_single_file_xsd` plumbing on both word/document.xml: error sets are IDENTICAL single-message sets ⇒ subtraction empty ⇒ gate passes — pinned by construction (first-unexpected-element semantics), re-executed @3b3fad96 (refinf_pass7_diag_p2control.py).
**Probe:** build two docx files whose `word/document.xml` contain the same bogus element `<w:bogus/>`; `python3 skills/docx/scripts/office/validate.py b.docx --original a.docx` exits 0 ("All validations PASSED!") while dropping `--original` exits 1. Executed @3b3fad96: rc=0 WITH `--original` vs rc=1 WITHOUT (re-executed byte-exact 2026-08-24 on minimal fixtures). ERRATUM: originally shipped as `python scripts/office/validate.py …` — wrong anchor dir; the script lives under `skills/docx/scripts/` and must be invoked from the repo root.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_code({ project: "skills", pattern: "_get_original_file_errors", limit: 5 });
```

## Verdict
Adopt baseline-diff validation for any pipeline that edits vendor/template documents: validate the ORIGINAL with the same validator, diff error sets position-free, gate only on new errors. Adapt schema paths to your host; keep the None-skip semantics (parts without schemas never fail). Omit the specific ignore list unless porting Word docs. Coverage caveat: no upstream unit tests pin this behavior; probes above were executed live.
