---
name: xml-markup-practices
description: "Use when designing or reviewing machine-readable XML formats, reuse-first schemas, RELAX NG namespaces, lowerCamelCase names, element/attribute rules, UTF-8 instances, and xmllint/RNG validation in CI."
disable-model-invocation: true
---

# XML Markup Practices

Application skill for Google XML Document Format Style Guide (archived `awesome-guidelines` capsules). For XHTML/HTML page markup, load `frontend-markup-practices`. For ODF/protobuf-generated XML, follow those format rules.

## Core Principle

Machine XML quality is **schema-first reuse with lowerCamelCase names and element/attribute discipline**, no mixed content, typed literals, UTF-8 instances validated against RELAX NG.

## When to Use / NOT

- Designing config/feed/RPC XML formats, RELAX NG schemas, instance samples.
- Reviewing namespace URIs, naming, element-vs-attribute choices, serialization.

**NOT when:**

- XHTML/HTML rich text, use HTML/CSS guides.
- ODF or protobuf-translated XML, host format wins.
- JSON API payloads, use `json-api-practices`.

## Workflow

1. **Schema/namespaces**, reuse, RELAX NG, xmlns (`xml-style-schema-namespaces.md`).
2. **Naming/values**, lowerCamelCase, dates, key-value (`xml-style-naming-values.md`).
3. **Elements/attributes**, mixed-content ban, tradeoffs (`xml-style-elements-attributes.md`).
4. **Instances/verify**, UTF-8, pretty-print, validate (`xml-style-instances-verify.md`).
5. **Verify**, `xmllint --relaxng` (or project validator) on changed schema/samples.

## Red Flags

- Greenfield format without reuse review
- Venetian Blind RELAX NG schema style
- Namespace-free new element names
- Single-letter namespace prefix
- PascalCase or snake_case XML names
- Mixed text and child elements in machine formats
- Useless wrapper around repeating siblings
- Attribute order assumed by consumers
- More than ~10 attributes without child grouping
- Multiline significant text in attributes
- Boolean flags instead of extensible enums
- `1`/`0` boolean tokens
- Non-RFC 3339 date/time literals
- Custom mini-language embedded in values
- Raw binary without Base64
- Comments carrying required protocol data
- Custom entity declarations beyond XML five
- Hand-rolled parser assuming pretty-print shape
- Random attribute/element soup
- Applying rules to XHTML body content
- Instance PR without schema validation

## Verification

- RELAX NG / XSD validates sample instances
- `xmllint --noout` on changed `.xml`
- Root default namespace + stable prefix map check
- lowerCamelCase name audit on new symbols
- Capsule checklist on element-vs-attribute choices


## References

- `awesome-guidelines/references/xml-style-learning-note.md`
- `awesome-guidelines/references/xml-style-schema-namespaces.md`
- `awesome-guidelines/references/xml-style-naming-values.md`
- `awesome-guidelines/references/xml-style-elements-attributes.md`
- `awesome-guidelines/references/xml-style-instances-verify.md`
