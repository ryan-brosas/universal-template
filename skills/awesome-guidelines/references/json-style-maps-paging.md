<!-- capsule-v2 -->
# Maps, paging, and ordering — are collections and links consistent?

**Source:** Google JSON style guide §JSON maps, §Paging, §Property ordering. **Question:** Are map keys documented and paging metadata coherent?

## Map vs object seam
**Path/Symbol:** JSON objects used as maps (e.g. thumbnails by pixel size).
**Signature:** map keys may be any Unicode; property-name rules don't apply.
**Data Shape:** square-bracket access in docs for map keys.

### Decisive pattern
```json
{
  "address": {
    "addressLine1": "123 Anystreet",
    "city": "Anytown"
  },
  "thumbnails": {
    "72": "https://cdn.example/72.png",
    "144": "https://cdn.example/144.png"
  }
}
```

**Flow:** document when object is a map vs structured record → maps use arbitrary string keys → structured objects keep camelCase property rules.
**Invariant:** pixel/size keys treated as camelCase properties without map documentation fails review.
**Probe:** API docs label map objects; clients use bracket notation examples.

## Paging seam
```json
{
  "data": {
    "currentItemCount": 10,
    "itemsPerPage": 10,
    "startIndex": 11,
    "totalItems": 2700000,
    "nextLink": "https://api.example/search?q=pizza&start=20",
    "previousLink": "https://api.example/search?q=pizza&start=0",
    "pageLinkTemplate": "https://api.example/search?q=pizza&start={index}",
    "items": []
  }
}
```

**Flow:** paging integers 1-based where specified → `nextLink`/`previousLink` for prev/next style → `pageLinkTemplate` for index templates → keep paging fields before `items`.
**Invariant:** inconsistent `startIndex` vs `pageIndex` math without documentation fails review.
**Probe:** pagination integration tests verify link templates and counts.

## Property ordering seam
**Flow:** when streaming parsers matter, order `kind` first and `items` last even though JSON objects are unordered by spec.
**Invariant:** `items` appearing before collection metadata in hand-authored fixtures fails review for Google-style APIs.
**Probe:** snapshot tests of canonical response files match ordering guideline.

## Verdict
Document maps, coherent paging metadata, kind-first/items-last for perf-friendly parsing. Learning note: `json-style-learning-note.md`.
