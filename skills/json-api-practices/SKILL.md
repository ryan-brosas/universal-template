---
name: json-api-practices
description: "Use when authoring or reviewing JSON API payloads, strict JSON syntax, camelCase properties, string enums, RFC3339 dates, Google-style data/error envelope, and paging reserved names."
disable-model-invocation: true
---

# JSON API Practices

Application skill for JSON style learning (from the archived `awesome-guidelines` style capsules). For HTTP resource design and versioning policy, load `api-design-practices`.

## Core Principle

JSON APIs are **strict JSON with predictable names and envelopes**, camelCase properties, standard string formats, and a consistent success/error shape when using the Google pattern.

## When to Use / NOT

- Public JSON request/response bodies, RPC wrappers, fixture files, OpenAPI examples.
- Reviewing API compatibility and reserved property usage.

**NOT when:**

- Non-JSON serialization (Protobuf, MessagePack), use stack conventions.
- Internal-only config JSON with project-specific rules, document divergence.

## Workflow

1. **Syntax**, quotes, camelCase, plural arrays, omit null (`json-style-syntax-properties.md`).
2. **Types**, enums, dates, durations, geo (`json-style-types-formats.md`).
3. **Envelope**, apiVersion, data/error, kind/items ordering (`json-style-envelope-errors.md`).
4. **Maps & paging**, map docs, paging links, ordering (`json-style-maps-paging.md`).
5. **Verify**, JSON parse + schema/OpenAPI validation on fixtures and samples.

## Red Flags

- Comments or trailing commas in JSON
- snake_case keys on JS-facing APIs
- Numeric enums without migration story
- Both `data` and `error` present
- Reserved names reused (`items`, `kind`, `error`)
- Non-RFC3339 date strings
- JS `undefined` serialized as null inconsistently

## Verification

- `jq` / `python -m json.tool` on fixtures
- OpenAPI/JSON Schema validation
- Contract tests for envelope + error shape
- Capsule checklist on API review

## Skill Result Contract

```xml
<skill_result>
  <skill>json-api-practices</skill>
  <status>success|partial|blocked|failure</status>
  <artifacts>json diff, schema validation output</artifacts>
  <evidence>learning note + capsule probes cited</evidence>
  <risks>invalid JSON, reserved name clash, bad date format, or none</risks>
</skill_result>
```

## References

- `awesome-guidelines/references/json-style-learning-note.md`
- `awesome-guidelines/references/json-style-syntax-properties.md`
- `awesome-guidelines/references/json-style-types-formats.md`
- `awesome-guidelines/references/json-style-envelope-errors.md`
- `awesome-guidelines/references/json-style-maps-paging.md`
