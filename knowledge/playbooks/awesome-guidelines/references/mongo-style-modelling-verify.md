<!-- capsule-v2 -->
# Modeling and verify — is embed/reference choice, nesting, validation, and indexing justified?

**Source:** MongoStyleGuide §Object modelling; MongoDB data modeling best practices. **Question:** Does schema match access patterns with bounded documents and enforced invariants?

## Modeling seam
**Path/Symbol:** MongoDB collections — document shape and relationships.
**Signature:** pruned top-level; bounded nesting; embed vs reference by query pattern.
**Data Shape:** nested `assessmentStates.foot`; separate `lessons` collection when embed explodes.

### Decisive pattern
```json
{
  "courseId": "course-42",
  "title": "Intro Mongo",
  "assessmentStates": {
    "foot": "COMPLETED",
    "eye": "NOT_REQUIRED"
  }
}
```

**Flow:** **prune flat growth** — merge related scalar states into nested objects (`assessmentStates.foot`) → avoid **excessive nesting** — split collection when depth hurts queries → **embed** when data queried/updated together, has-a relationship, bounded size → **reference** when child cardinality high, embed grows unbounded, child independent, or duplication hard to maintain → duplicate only with **staleness plan** (immutable/temporal OK; stock counts need transactions/triggers) → add **`$jsonSchema` validation** on enums, types, required fields → **index** filter/sort/`$lookup` fields — monitor write ratio → plan schema **early and iterate** before production scale → don't rely on **multi-doc transactions** to fix embed/reference mistakes.
**Invariant:** unbounded embedded array without archival/reference plan, or hot query without index, fails modeling review.
**Probe:** explain() on primary queries; validation rules in collMod; document size stats; relationship cardinality checklist vs MongoDB embed table.

## Verify seam
**Flow:** MongoStyleGuide field rules + MongoDB official embed/reference table → Compass schema view or `$jsonSchema` → index coverage on production query log → migration plan when breaking shape changes.
**Probe:**
```javascript
db.collection.getIndexes();
db.runCommand({ collMod: 'students', validator: { $jsonSchema: { /* ... */ } } });
```

## Verdict
Access-pattern-driven embed/reference, bounded nesting, validation + indexes on hot paths. Learning note: `mongo-style-learning-note.md`.
