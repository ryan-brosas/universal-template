<!-- capsule-v2 -->
# Types and formats — are values typed correctly with standard string formats?

**Source:** Google JSON style guide §Property value types, §Standard data types. **Question:** Do enums, dates, and geo fields serialize predictably across clients?

## Scalar types seam
**Path/Symbol:** JSON property values in public API schemas.
**Signature:** boolean | number | string | object | array | null only.
**Data Shape:** enums as strings; formatted strings for dates/geo/durations.

### Decisive pattern
```json
{
  "canPigsFly": null,
  "areWeThereYet": false,
  "answerToLife": 42,
  "name": "Bart",
  "color": "WHITE",
  "lastUpdate": "2007-11-06T16:34:41.000Z",
  "duration": "P3Y6M4DT12H30M5S",
  "statueOfLiberty": "+40.6894-074.0447"
}
```

**Flow:** enums as strings (not numbers) → dates RFC 3339 → durations ISO 8601 → lat/long ISO 6709 `±DD.DDDD±DDD.DDDD`.
**Invariant:** numeric enum codes and Unix epoch numbers where string format is standard fail review.
**Probe:** JSON Schema / OpenAPI documents string formats; sample fixtures validate regex/RFC parsers.

## Structure vs flat seam
```json
{
  "company": "Google",
  "website": "https://www.google.com/",
  "address": {
    "line1": "111 8th Ave",
    "line2": "4th Floor",
    "city": "New York",
    "state": "NY",
    "zip": "10011"
  }
}
```

**Flow:** flatten when grouping is convenience-only → nest when sub-object is semantic (address, thumbnail map documented as structure).
**Invariant:** wrapper object with single child that could be flattened fails review.
**Probe:** schema review asks whether nesting matches domain model.

## Verdict
String enums, RFC3339 dates, ISO8601 durations, ISO6709 geo, semantic nesting only. Learning note: `json-style-learning-note.md`.
