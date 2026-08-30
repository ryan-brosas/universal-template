<!-- capsule-v2 -->
# Naming and values — are identifiers lowerCamelCase and literals typed?

**Source:** Google XML style §4, §7–9. **Question:** Do names, numbers, dates, and key-value pairs parse without ad hoc mini-languages?

## Naming seam
**Path/Symbol:** element names, attribute names, enumeration tokens.
**Signature:** lowerCamelCase; ASCII letters/digits; ≤25 chars when practical.
**Data Shape:** RFC 3339 timestamps; SI units on measured key-value attrs.

### Decisive pattern
```xml
<measurement xmlns="https://example.com/metrics/2024">
  <distance value="12.5" unit="m" />
  <status>ready</status>
  <observedAt>2024-06-01T15:04:05Z</observedAt>
</measurement>
```

**Flow:** name elements, attributes, and enum values lowerCamelCase starting with lowercase letter → use ASCII letters and digits only → keep names ≤25 characters when still clear; prefer concise informative words over obscure abbreviations → treat acronyms as words (`informationUri`, not `informationURI`) → use published standard abbreviations only when widely known → numeric values: prefer 32-bit int, 64-bit long, or 64-bit double in base 10 → avoid booleans; prefer enumerations; if bool required use `true`/`false` only (not `1`/`0`) → dates/times in RFC 3339; prefer UTC → do not embed custom syntax in values except well-known forms (dates, URIs, XPath) → define whitespace stripping rules for parsers → represent simple key-value pairs as empty element named for key with `value` attribute; optional `unit` in SI → for huge key sets use generic element with `key`/`value`/`scheme` plus external key registry → binary payload Base64-encoded only; optional `xsi:type="xs:base64Binary"`.
**Invariant:** snake_case/PascalCase names, ad hoc abbreviations, non-RFC3339 dates, or raw binary in text nodes fail naming/value review.
**Probe:** name casing grep; date parse RFC3339; Base64-only binary check.

## Key-value seam
**Flow:** empty element + `value` attr for bounded keys; generic key attr only when key space is open.
**Invariant:** repeating `foo1`/`foo2` attribute pattern instead of repeatable element fails value model review.
**Probe:** repeating-field schema walk.

## Verdict
lowerCamelCase ASCII names, typed literals, RFC 3339 time, Base64 binary, key-value attr pattern. Learning note: `xml-style-learning-note.md`.
