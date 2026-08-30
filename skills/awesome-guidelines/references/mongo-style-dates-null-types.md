<!-- capsule-v2 -->
# Dates, null, and types — are BSON types consistent with MongoStyleGuide null semantics?

**Source:** MongoStyleGuide §Dates, §Null and undefined, §Other types. **Question:** Do date, null, and scalar fields avoid mixed types and overloaded missing values?

## Type seam
**Path/Symbol:** MongoDB document fields — scalars, dates, arrays, subdocuments.
**Signature:** one type per column; Date vs day string; null rules differ by shape.
**Data Shape:** ISODate timestamps; `'YYYY-MM-DD'` calendar days; `{ state, value }` for multi-absence.

### Decisive pattern
```json
{
  "createdAt": { "$date": "2017-04-14T06:41:21.616Z" },
  "dateOfBirth": "1989-10-03",
  "notes": "",
  "comments": [],
  "height": null,
  "weight": { "state": "SET", "value": 97 }
}
```

**Flow:** persist instants as **BSON Date** — never ISO **strings** from JSON deserialization → calendar-only dates → **`'YYYY-MM-DD'` strings** → use `null`/`undefined` only for **unset**, not business meaning → prefer defaults **`''`, `0`, `[]`** over null when type allows → **primitives**: absent → **`null`** consistently (don't mix null and missing in same field) → **objects/arrays**: **omit field** when absent — not `null` or empty array for "N/A" when type differs by product → need two absence meanings → **`{ state, value }`** wrapper → **one BSON type per field** → homogeneous object schema in arrays → don't use **`0`/`''` as unknown** — use `null` → numbers **numeric** except phone/ID strings with leading zeros → units as **`{ unit, value }`**.
**Invariant:** ISO date string column, mixed-type field, or null+missing in same field path fails type review.
**Probe:** `$jsonSchema` bsonType checks; aggregate `$type` on suspect fields; spot-check JSON import path.

## Verdict
Correct Date vs day-string split, pure null semantics, homogeneous columns, numeric BSON. Learning note: `mongo-style-learning-note.md`.
