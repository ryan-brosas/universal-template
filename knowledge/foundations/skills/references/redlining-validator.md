<!-- capsule-v2 -->
# Redlining Validator — how does a validator PROVE every edit in a redlined DOCX is properly tracked?

**Source:** anthropics/skills (source-available per LICENSE.txt) `main@3b3fad96`; Codebase Memory `mnt-hdd-utopia-inspo-reference-skills`. **Question:** How can untracked edits be detected mechanically, and how are another author's changes rejected without breaking tracking?

## Undo-the-new-changes-then-compare validation
**Path/Symbol:** `skills/docx/scripts/office/validators/redlining.py::RedliningValidator.validate` (:38–88) + `_new_tracked_changes` (:112–149) + `_remove_tracked_changes` (:252–280); helpers `rendered_text`/`safe_extract` from `office/helpers`.
**Signature:** `validate() -> bool` (prints FAILED diagnostics or PASSED with change count); `repair() -> 0` by design — detection-only validator.
**Data Shape:** tracked-change identity key = `(tag, w:author, w:date, rendered_text)` where rendered_text concatenates `w:t` + `w:delText` descendants honoring xml:space="preserve" (:107–110). "New" = modified-doc ins/del elements whose key has NO bucket left in the original's key→elements pool. Comparison universe: paragraph texts joined by `\n` from `.//w:p` → `.//w:t` (:282–295).

### Decisive source
```python
new_changes = self._new_tracked_changes(original_root, modified_root)
self._remove_tracked_changes(modified_root, new_changes)
modified_text = self._extract_text_content(modified_root)
original_text = self._extract_text_content(original_root)
if modified_text != original_text:
    error_message = self._generate_detailed_diff(original_text, modified_text)
```
```python
for elem in to_process:            # _remove_tracked_changes, del branch:
    ...                            # delText->t retag THEN splice children out
for elem in del_elem.iter():
    if elem.tag == deltext_tag:
        elem.tag = t_tag           # rejecting a deletion = keep its text as real text
for child in reversed(list(del_elem)):
    parent.insert(del_index, child)
parent.remove(del_elem)
```

**Flow:** parse both document.xml trees (original unpacked via safe_extract into temp) → pool original ins/del by identity key; walk modified's ins/del matching buckets → leftovers = NEW changes → simulate acceptance of ONLY the new ones (remove new `<w:ins>` subtrees; retag new `<w:del>`'s delText to t and hoist children) → extract both texts → any residual difference is an UNTRACKED edit → fail with a word-diff (`git diff --word-diff=plain --word-diff-regex=. -U0 --no-index`, char-level first, word fallback) plus a four-cause diagnostic block.
**Invariant:** The trick that makes this sound: after removing all NEW tracked changes and un-doing them textually, the result must equal the ORIGINAL byte-for-byte at the text level — anything else was edited outside tracking. Rejecting another author's change has exactly three legal shapes, encoded in the diagnostics: nest `<w:del>` inside their `<w:ins>` (splitting their ins is legal ONLY if every piece keeps author+date and together spells the same text — otherwise the identity matcher reads it as new); restore their deletion with your own `<w:ins>` AFTER their `<w:del>`; never rewrite their element's text. Only w:ins/w:del are matched — format-only revisions (w:rPrChange etc.) don't participate. Headers/footers/footnotes/endnotes are OUT of scope by docstring (separate parts, unchecked).
**Probe:** No upstream tests. Deterministic probes (anchors re-derived & executed 2026-08-24): `grep -c 'def _tracked_change_key' skills/xlsx/scripts/office/validators/redlining.py` = 1; `grep -c 'word-diff-regex' skills/xlsx/scripts/office/validators/redlining.py` = 1. ERRATUM: the original second clause claimed `word-diff-regex` = 2 — the xlsx twin carries it exactly ONCE (`--word-diff-regex=.` at :197); the docx twin (`skills/docx/scripts/office/validators/redlining.py`) also counts 1. Behavioral caveat stands: full proof needs a docx corpus.
**Coverage caveat:** recorded honestly — no direct test suite pins this module upstream.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-reference-skills", query: "RedliningValidator", limit: 5 });
// skills.skills.docx.scripts.office.validators.redlining.RedliningValidator.validate Method redlining.py 38-88
```

## Verdict
Adopt the undo-new-then-compare strategy for ANY tracked-changes format (it generalizes beyond OOXML), the author+date+text identity key for change matching, and the three rejection patterns as API documentation. Adapt namespaces/text-extraction to your format. Omit nothing else — repair stays a no-op on purpose (multi-valid fixes need an author).
