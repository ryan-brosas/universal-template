<!-- capsule-v2 -->
# Elements vs attributes — is structure element-first without mixed content?

**Source:** Google XML style §5–6, §12. **Question:** Are repeating data, multiline text, and metadata placed using the guide's element/attribute tradeoffs?

## Structure seam
**Path/Symbol:** schema design and sample instances for machine XML.
**Signature:** no mixed content; attribute order irrelevant; ~≤10 attributes per element.
**Data Shape:** metadata/ids in attributes; payload/repeats in elements.

### Decisive pattern
```xml
<entry xmlns="https://example.com/catalog/2024"
       xml:id="entry-9"
       status="active">
  <title>Widget</title>
  <description>Multi-line
human readable text belongs in an element.</description>
  <tag>hardware</tag>
  <tag>popular</tag>
</entry>
```

**Flow:** elements contain only empty, text-only, or child-only content — never mixed text+children in machine formats → do not add wrapper elements whose only job is repeating homogeneous children → designs MUST NOT depend on attribute order → cap attributes at ~10; group related fields as child elements for forward extensibility → never store line-break-significant text in attributes → allow either quote style in instances; specs must not require one quote form → use elements when data repeats, has substructure, needs order, spans lines, is large/streamable, or needs `xml:lang` → use attributes for enum codes, metadata roles, IDs/references (`xml:id`), hrefs, inherited flags (`xml:lang`, `xml:space`), and whitespace-separated token lists → prefer consistent metadata-in-attributes / data-in-elements split over random mixtures → when extending foreign schemas, mirror their element/attribute style.
**Invariant:** mixed content model, multiline prose in attributes, or attribute order assumptions fail structure review.
**Probe:** XSD/RNG mixed=false; multiline attribute scan; parser order-independence test.

## Wrapper seam
**Flow:** repeating siblings without extra list wrapper (Atom-style).
**Invariant:** `<items><item/><item/></items>` wrapper with no other semantics fails wrapper review unless host format requires it.
**Probe:** homogeneous repeat pattern audit.

## Verdict
No mixed content, element-first payloads, attribute-bounded metadata, explicit elem/attr decision rules. Learning note: `xml-style-learning-note.md`.
