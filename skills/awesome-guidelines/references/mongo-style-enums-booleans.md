<!-- capsule-v2 -->
# Enums and booleans — are states UPPERCASE strings with explicit values and proper boolean prefixes?

**Source:** MongoStyleGuide §Enumerations, §Booleans. **Question:** Do enum and boolean fields self-document and forbid invalid multi-flag combinations?

## Enum seam
**Path/Symbol:** MongoDB collection documents — categorical string fields.
**Signature:** UPPERCASE string constants; no null/undefined enum members.
**Data Shape:** `'MALE'|'FEMALE'` not `0|1`; sets as `['DOLPHIN','BEE']`.

### Decisive pattern
```json
{
  "assessmentState": "NOT_REQUIRED",
  "gender": "MALE",
  "tags": ["URGENT", "REVIEW"]
}
```

**Flow:** model enumerations as **UPPERCASE string constants** (`'WAITING'`, `'IN_PROGRESS'`) — never numeric or boolean codes → include **explicit states** for unknown/N/A (`'NOT_APPLICABLE'`) — never `null`, missing, or title-case mixed with constants → model **sets** as arrays of uppercase enum strings → for two-value concepts that are **not natural booleans** or may grow beyond two states, use **enum not boolean** (`gender: 'MALE'` not `false`) → real booleans: prefix **`is`/`has`/`did`** (`isDoctor`, `hasDiabetes`) → **merge mutually exclusive booleans** into one enum (`color: 'BLUE'` not `isRed`+`isBlue`+`isGreen`).
**Invariant:** numeric enum, null enum state, or simultaneous true exclusive flags fails Mongo schema review.
**Probe:** sample aggregate `$group` on enum fields; grep `"isRed"|"isBlue"`; validate allowed enum list in `$jsonSchema`.

## Verdict
UPPERCASE self-documenting enums, explicit absent states, prefixed booleans, exclusive flags as single enum. Learning note: `mongo-style-learning-note.md`.
