# JSON style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `json-style-*.md` capsules, `json-api-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [Google JSON Style Guide](https://google.github.io/styleguide/jsoncstyleguide.xml) (primary) | no comments; double quotes; camelCase property names; plural arrays; structured vs flat data; map keys exception; string enums; RFC3339/ISO8601/ISO6709 formats; data/error envelope; reserved property names; kind first / items last; omit null when optional |
| [JSON.org / RFC 8259](https://www.json.org/) (secondary) | valid JSON value types only; no JS expressions in JSON |

**Not duplicated here:** Full OpenAPI/JSON Schema authoring — use `api-design-practices`. Google-specific reserved property catalog in full — capsules capture probes; see source for exhaustive list.

## Mental model

JSON API style in this catalog is **strict JSON syntax plus Google envelope conventions**:

1. **Syntax** — valid JSON only; double-quoted keys/strings; camelCase identifiers; plural array names.
2. **Semantics** — flatten when possible; nest when structure is meaningful; drop optional null/empty fields.
3. **Types** — booleans/numbers/strings/objects/arrays/null; enums as strings; standard string formats for dates/durations/geo.
4. **Envelope** — top-level `apiVersion`; exactly one of `data` or `error`; paging/link reserved names; `kind` first, `items` last in collections.

## Decision tables

### Property naming

| Rule | Detail |
|---|---|
| Case | camelCase ASCII |
| Start char | letter, `_`, or `$` |
| Arrays | plural property names (`items`, `siblings`) |
| Singular | non-array fields singular (`author`) |
| Maps | any Unicode key when documented as map |
| Reserved | avoid reusing Google reserved names for other semantics |

### Values

| Type | Rule |
|---|---|
| Allowed | boolean, number, string, object, array, null |
| Forbidden | JS identifiers/functions unquoted |
| Enums | string values (`"WHITE"`) |
| Dates | RFC 3339 strings |
| Durations | ISO 8601 strings |
| Lat/long | ISO 6709 string `±DD.DDDD±DDD.DDDD` |
| Optional null | omit property unless semantic zero/false distinction |

### Envelope (when using Google pattern)

| Field | Role |
|---|---|
| `apiVersion` | API version string |
| `data` | success payload |
| `error` | error payload (wins if both present) |
| `context` | client correlation id |
| `data.kind` | type discriminator (first in object) |
| `data.items` | collection (last in data object) |

### Errors

| Field | Role |
|---|---|
| `error.code` | usually HTTP-like code |
| `error.message` | human summary |
| `error.errors[]` | detailed error objects (domain, reason, message) |

## Anti-patterns

- Comments inside JSON payloads
- Single-quoted keys/strings
- snake_case property names in JS-facing APIs
- Numeric enums without migration plan
- Arbitrary grouping objects for convenience
- `data` and `error` together (error must win)
- `kind` not first in typed objects
- `items` before pagination metadata
- JavaScript `undefined` or functions in JSON

## Skill trace

| Artifact | Role |
|---|---|
| `json-style-syntax-properties.md` | quotes, names, pluralization, omit null |
| `json-style-types-formats.md` | enums, dates, durations, geo |
| `json-style-envelope-errors.md` | apiVersion, data/error, reserved names |
| `json-style-maps-paging.md` | maps vs objects, paging, ordering |
| `json-api-practices/SKILL.md` | jsonlint/schema validation in CI |
