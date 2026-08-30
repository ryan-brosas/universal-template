<!-- capsule-v2 -->
# Instances and verification — are serialized documents UTF-8 and parser-safe?

**Source:** Google XML style §10–11. **Question:** Do hand-written or generated instances follow encoding/whitespace rules and validate with standard parsers?

## Instance seam
**Path/Symbol:** `.xml` instance documents on disk or wire.
**Signature:** UTF-8; namespaces on root; 2-space pretty-print; no comment-as-data.
**Data Shape:** standard entity set; optional CDATA equivalent to escaped text.

### Decisive pattern
```xml
<?xml version="1.0" encoding="UTF-8"?>
<catalog xmlns="https://example.com/catalog/2024">
  <entry xml:id="entry-1" status="draft">
    <title>Example</title>
  </entry>
</catalog>
```

**Flow:** serialize with UTF-8 unless extraordinary reason → declare namespaces on root element; keep URI↔prefix mapping constant in doc and specification → use well-known prefixes in docs (`html:`, `dc:`, `xs:`) where applicable → pretty-print with 2-space child indent; do not wrap elements that contain character content (wrapping changes values) → one space before each attribute; break long start-tags after non-final attributes if needed → treat `<tag/>` and `<tag></tag>` as equivalent → do not rely on redundant whitespace inside tags → comments MUST NOT carry protocol data; avoid comments on publicly transmitted docs; if used, keep out of character-content-only elements → only standard entities `& < > " '`; prefer literal Unicode in UTF-8 → do not invent new processing instructions except local conventions → validate with standards-compliant parsers, never layout-assuming hand parsers → gzip repetitive docs instead of over-terse attribute encoding.
**Invariant:** non-UTF-8 default, comments as required fields, custom entities, or parser depending on pretty-print layout fails instance review.
**Probe:** `xmllint --noout`; encoding declaration check; comment-in-leaf-text grep.

## Verify seam
**Flow:** RELAX NG (or published XSD) validate instances in CI; Schematron for cross-field rules when present.
**Invariant:** instance sample in PR without schema validation fails verify gate.
**Probe:** `xmllint --relaxng` / project validator on changed XML.

## Verdict
UTF-8 instances, stable namespace declarations, 2-space pretty-print discipline, schema validation in CI. Learning note: `xml-style-learning-note.md`.
