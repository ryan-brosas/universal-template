<!-- capsule-v2 -->
# Syntax and properties — is payload valid strict JSON with camelCase names?

**Source:** Google JSON style guide §General rules, §Property names. **Question:** Will parsers accept the JSON and can JS clients use dot notation?

## Valid JSON seam
**Path/Symbol:** API request/response JSON bodies.
**Signature:** double-quoted keys; no comments; camelCase property names.
**Data Shape:** plural names for arrays; singular for scalars/objects.

### Decisive pattern
```json
{
  "apiVersion": "1.0",
  "data": {
    "recipeName": "pizza",
    "ingredients": ["tomatoes", "cheese", "sausage"]
  }
}
```

**Flow:** strict JSON only → double quotes on all property names and string values → numbers/booleans unquoted → no trailing comments.
**Invariant:** comments, single quotes, or unquoted JS identifiers in JSON fail review.
**Probe:** `python -m json.tool` / `jq .` parse succeeds; JSON linter clean.

## Naming seam
```json
{
  "author": "lisa",
  "siblings": ["bart", "maggie"],
  "totalItems": 10,
  "thisPropertyIsAnIdentifier": true
}
```

**Flow:** camelCase meaningful names → avoid JS reserved words for dot access → arrays plural (`siblings`) → scalars singular (`author`).
**Invariant:** `snake_case`, Hungarian prefixes (`sp_`), and reserved word property names fail review on public API.
**Probe:** grep `"[a-z]+_[a-z]+"` keys in API fixtures; reserved-word list check.

## Omit null seam
```json
{
  "volume": 10,
  "balance": 0
}
```

**Flow:** drop optional null/empty properties unless zero/false carries meaning (`balance: 0` kept).
**Invariant:** `"currentlyPlaying": null` on optional field fails review unless documented semantic need.
**Probe:** response fixtures omit absent optional fields; OpenAPI `required` matches reality.

## Verdict
Strict JSON, camelCase, plural arrays, omit meaningless nulls. Learning note: `json-style-learning-note.md`.
