---
title: json-api-practices
summary: Use when authoring or reviewing JSON API payloads, strict JSON syntax, camelCase properties, string enums, RFC3339 dates, Google-style data/error envelope, and paging reserved names.
kind: playbook
---

# JSON API Practices

Application skill for JSON style. For HTTP resource design and versioning policy, load `api-and-interface-design`.

## Core Principle

JSON APIs are **strict JSON with predictable names and envelopes**, camelCase properties, standard string formats, and a consistent success/error shape when using the Google pattern.

## When to Use / NOT

- Public JSON request/response bodies, RPC wrappers, fixture files, OpenAPI examples.
- Reviewing API compatibility and reserved property usage.

**NOT when:**

- Non-JSON serialization (Protobuf, MessagePack), use stack conventions.
- Internal-only config JSON with project-specific rules, document divergence.

## Workflow

1. **Syntax**, quotes, camelCase, plural arrays, omit null.
2. **Types**, enums, dates, durations, geo.
3. **Envelope**, apiVersion, data/error, kind/items ordering.
4. **Maps & paging**, map docs, paging links, ordering.
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
