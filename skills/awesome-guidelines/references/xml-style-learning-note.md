# XML format style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `xml-style-*.md` capsules, `xml-markup-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [Google XML Document Format Style Guide](https://google.github.io/styleguide/xmlstyle.html) (primary) | Reuse formats; RELAX NG compact salami slice; namespaces; lowerCamelCase names; no mixed content; attribute/element tradeoffs; RFC 3339 dates; instance UTF-8 pretty-print |
| [Google Style Guides index](https://google.github.io/styleguide/) (secondary) | XML guide applies when **creating new machine-readable formats**; not XHTML/ODF; elements-vs-attributes design aid |
| [Google documentation philosophy](https://google.github.io/styleguide/docguide/philosophy.html) (secondary) | Readable plain source; consistency over cleverness — aligns with instance formatting discipline |

**Scope:** Machine-generated/consumed XML formats (config, feeds, RPC payloads). **Not** XHTML/HTML-like rich text, ODF, or protobuf-translated formats — follow those ecosystems instead. Machine-interpretable islands inside rich docs SHOULD follow this guide.

## Mental model

XML format quality is **schema-first reuse + predictable names + element/attribute discipline**:

1. **Schema/namespaces** — reuse/extend existing formats; express with RELAX NG; default namespace; stable URI.
2. **Naming/values** — lowerCamelCase ASCII; concise names; typed literals; no embedded mini-languages.
3. **Elements/attributes** — no mixed content; attribute budget; decision rules for metadata vs payload.
4. **Instances/verify** — UTF-8, 2-space pretty-print, no comment-as-data; validate with standard parsers.

## Decision tables

### Design gate (§1–3)

| Case | Rule |
|---|---|
| New format | reuse/extend first; wide review before inventing |
| Extension | match host format style even if it contradicts this guide |
| Schema | SHOULD use schema language; prefer RELAX NG compact, salami slice |
| Schematron | MAY embed for cross-field rules |
| Namespace elements | MUST be namespaced; default namespace SHOULD |
| Namespace attrs | SHOULD NOT be namespaced (except foreign) |
| Namespace URI | `https://example.com/whatever/year` pattern |
| Prefixes | short lowercase ASCII; no single-letter |

### Names & values (§4, §7–9)

| Entity | Convention |
|---|---|
| Elements/attrs/enums | lowerCamelCase |
| Characters | ASCII letters + digits only |
| Length | SHOULD ≤25 chars unless obscure shorter is worse |
| Acronyms | treat as words (`informationUri`) |
| Numbers | int/long/double base-10; avoid booleans (use enums) |
| Booleans if needed | `true`/`false` only |
| Dates | RFC 3339; prefer UTC |
| Key-value | empty element + `value` attr; optional `unit` (SI) |
| Binary | Base64 only; optional `xsi:type=xs:base64Binary` |
| Embedded syntax in values | avoid except dates/URIs/XPath |

### Elements & attributes (§5–6, §12)

| Case | Rule |
|---|---|
| Element content | children **or** text, not mixed |
| Wrapper lists | avoid repeating-child wrapper elements |
| Attribute order | MUST NOT matter |
| Attribute count | ≤~10; prefer child elements |
| Multiline text | element not attribute |
| Ordered data | elements (attrs unordered) |
| IDs/refs | attribute, prefer `xml:id` |
| Codes/enums | attribute when possible |
| Metadata on data | attribute when possible |
| Large/repeatable | element for streaming/repeat |

### Instance representation (§11)

| Topic | Rule |
|---|---|
| Encoding | UTF-8 SHOULD |
| Root | declare namespaces on root |
| Prefix map | constant through document + docs |
| Indent | 2-space pretty-print OK |
| Char-content elements | do not wrap (changes value) |
| Empty elements | `<tag/>` or `<tag></tag>` equivalent |
| Comments | not for real data; avoid on the wire |
| Entities | only standard five; prefer literal UTF-8 chars |
| PIs | avoid new ones |

## Anti-patterns

- Inventing new XML format without reuse review
- Venetian Blind schema style with RELAX NG
- Namespace-free new designs
- Single-letter namespace prefixes
- upperCamelCase or snake_case element names
- Mixed content in machine formats
- Wrapper element around homogeneous repeats only
- >10 attributes on one element without child grouping
- Multiline significant text in attributes
- Boolean flags instead of extensible enumerations
- `1`/`0` boolean tokens
- Ad hoc date formats or local time without reason
- Mini-languages embedded in attribute values
- Raw binary bytes in XML
- Comments carrying protocol data
- Custom entity declarations
- Hand-rolled parser assuming pretty-print layout
- Random attribute/child soup without metadata/data split
- Applying this guide to XHTML body markup
- Schema change without extreme need (namespace churn)

## Skill trace

| Artifact | Role |
|---|---|
| `xml-style-schema-namespaces.md` | reuse, RELAX NG, namespaces |
| `xml-style-naming-values.md` | lowerCamelCase, literals, key-value |
| `xml-style-elements-attributes.md` | mixed content ban, elem vs attr |
| `xml-style-instances-verify.md` | UTF-8 instances, comments, validate |
| `xml-markup-practices/SKILL.md` | RNG validate + instance lint in CI |
