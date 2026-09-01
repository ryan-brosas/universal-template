---
name: mongodb-data-practices
description: "Use when designing or reviewing MongoDB schemas, UPPERCASE enums, is/has booleans, BSON dates, null semantics, camelCase keys, string _id, embed vs reference, validation, and indexes."
disable-model-invocation: true
---

# MongoDB Data Practices

Application skill for jsoendermann MongoStyleGuide + MongoDB official data-modeling ingest (`awesome-guidelines`). Application-layer JS/Node: also `node-coding-practices` / `javascript-coding-practices`.

## Core Principle

Mongo schema quality is **self-documenting BSON aligned to read patterns**, explicit enum states, consistent null semantics, camelCase keys, and embed/reference choices driven by access patterns not premature scale fantasies.

## When to Use / NOT

- Designing new collections, migrations, `$jsonSchema` validators.
- Reviewing BSON documents, seed data, aggregation inputs.
- Choosing embed vs reference for related entities.

**NOT when:**

- SQL relational schemas, `sql-scripting-practices`.
- MongoDB server C++ contributions, upstream server styleguides.
- Generic API JSON without Mongo persistence, `json-api-practices`.

## Workflow

1. **Enums/booleans**, UPPERCASE strings, prefixes, merge flags (`mongo-style-enums-booleans.md`).
2. **Dates/null/types**, Date vs day string, homogeneous columns (`mongo-style-dates-null-types.md`).
3. **Names/IDs**, camelCase, collections, string `_id` (`mongo-style-names-ids.md`).
4. **Modeling**, nesting, embed/reference, validation, indexes (`mongo-style-modelling-verify.md`).
5. **Verify**, `$jsonSchema`, index explain, sample doc audit.

## Red Flags

- Numeric or boolean enum codes
- `null` / missing as enum "unknown"
- Title-case enum mixed with UPPERCASE constants
- Mutually exclusive boolean triplets
- ISO date strings persisted instead of BSON Date
- Date type for birthdate-only fields
- Business meaning overloaded onto null/undefined
- null and missing mixed in same field path
- `null` instead of `''` or `[]` defaults
- Mixed BSON types in one field
- Heterogeneous object shapes in array columns
- `0` or `''` as "unknown" sentinel
- Numeric strings for arithmetic fields
- ObjectId `_id` with app serialization bugs
- snake_case field keys in JS-first apps
- Unbounded embedded arrays without reference split
- Deep nesting without subdocument justification
- Transactions compensating for bad embed choice
- Hot queries without supporting indexes
- Abbreviated field names outside domain DSL

## Verification

- `$jsonSchema` or validator on changed collections
- `$type` / sample audit on enum and date fields
- Embed/reference checklist vs MongoDB official table
- `explain()` on primary read paths; index list matches filters/sorts
- Capsule probes cited in review notes


## References

- `awesome-guidelines/references/mongo-style-learning-note.md`
- `awesome-guidelines/references/mongo-style-enums-booleans.md`
- `awesome-guidelines/references/mongo-style-dates-null-types.md`
- `awesome-guidelines/references/mongo-style-names-ids.md`
- `awesome-guidelines/references/mongo-style-modelling-verify.md`

## Related skills

- `node-coding-practices`, Node app code reading/writing documents
- `javascript-coding-practices`, app-layer validation and types
- `sql-scripting-practices`, when data lives in SQL instead
