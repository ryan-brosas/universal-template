<!-- capsule-v2 -->
# Names and IDs — are keys camelCase with plural collections and string _id over ObjectId?

**Source:** MongoStyleGuide §Names, §Other types (ObjectIds). **Question:** Do collection and field naming align with JavaScript consumers and avoid ObjectId serialization pain?

## Naming seam
**Path/Symbol:** MongoDB collection names and document field keys.
**Signature:** camelCase keys; plural camelCase collections; string `_id`.
**Data Shape:** `users`, `users.appointments`; `appointmentTime` not `apTime`.

### Decisive pattern
```json
{
  "_id": "6xAySKn98aZ66vN",
  "appointmentTime": "2026-08-28T08:00:00.000Z",
  "HISNumber": "HIS-99102",
  "ABIRight": 1.12
}
```

**Flow:** field keys → **camelCase** (not snake_case) → avoid abbreviations except **domain DSL** (`ABIRight`, `HISNumber`) — spell out general terms (`appointmentTime` not `apTime`) → collection names → **plural camelCase** → related namespaces with **dots** (`users`, `users.appointments`) → **`_id`**: set explicitly — natural unique business key or random string — **avoid ObjectId** when app serialization is fragile → prefer **least surprise** over writer shortcuts (MongoStyleGuide general rule).
**Invariant:** snake_case field keys, singular collection name, or ObjectId-only _id without documented reason fails naming review.
**Probe:** list collections; sample 20 docs for key casing; grep `_id` type in app layer.

## Verdict
camelCase plural collections, readable keys, explicit string _id. Learning note: `mongo-style-learning-note.md`.
