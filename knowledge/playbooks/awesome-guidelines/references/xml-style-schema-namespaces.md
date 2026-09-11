<!-- capsule-v2 -->
# Schema and namespaces — is the format reused and formally bounded?

**Source:** Google XML style §1–3. **Question:** Was an existing format extended before inventing a new one, and is RELAX NG the source of truth?

## Design seam
**Path/Symbol:** new machine-readable XML format specs (`.rng`, design docs).
**Signature:** reuse-first; RELAX NG compact salami slice; default namespace on elements.
**Data Shape:** schema + normative prose; optional Schematron overlays.

### Decisive pattern
```xml
<!-- Instance root (namespace declared once) -->
<feed xmlns="https://example.com/orderFeed/2024">
  <orderId>42</orderId>
  <createdAt>2024-06-01T12:00:00Z</createdAt>
</feed>
```

**Flow:** attempt to reuse or extend existing XML formats before designing anew — get wide review for greenfield formats → when extending, follow the host format's implicit style even if it contradicts this guide → express formats with a schema language; prefer RELAX NG compact syntax with salami-slice rules (one rule per element); Russian Doll only for short/simple schemas; do not use Venetian Blind with RELAX NG → embed Schematron for cross-element constraints when needed → provide regex hints for complex literal values → MAY ship DTD/XSD copies for legacy tooling only → put elements in a namespace; use default namespace on new designs → keep attribute names unprefixed unless foreign → namespace URIs like `https://example.com/whatever/year`; do not change namespaces unless semantics break compat → namespace prefixes: short lowercase ASCII; never single-letter.
**Invariant:** greenfield format without reuse note, namespace-free elements, or Venetian Blind RELAX NG layout fails design review.
**Probe:** design doc reuse section; RNG salami-slice check; root default namespace present.

## Stability seam
**Flow:** namespace URI stable across compatible revisions; prefix map documented and constant in instances.
**Invariant:** namespace churn on non-breaking field add fails compat review.
**Probe:** version diff on targetNamespace / xmlns values.

## Verdict
Reuse-first format design, RELAX NG compact salami slice, default element namespace. Learning note: `xml-style-learning-note.md`.
