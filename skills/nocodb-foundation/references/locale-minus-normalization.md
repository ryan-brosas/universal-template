<!-- capsule-v2 -->
# locale minus-sign paste normalization — why must U+2212 be normalized and the sign resolved AFTER stripping?

**Source:** NocoDB AGPL-3.0 `develop@640fe3b06fb2`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** Pasting a copied negative cell back in 36 locales dropped its sign — what ordering of normalize→strip→sign-resolve fixes every case at once?

## Connected graph-selected seam
**Path/Symbol:** `packages/nocodb-sdk/src/lib/columnHelper/utils/serializer.ts:serializeDecimalValue` (:64 U+2212 normalize; :91–:96 strip keeps '-'; :121–:127 sign resolution) + `serializeCurrencyValue` en-US fast path keeping '-'.
**Signature:** `serializeDecimalValue(value: string, callback, params): number | null | SilentTypeConversionError`.
**Data Shape:** phase 1 = normalize U+2212→'-' then strip noise KEEPING every '-'; phase 2 = `isNegative = cleaned.startsWith('-')`, strip remaining '-', re-attach only if leading.

### Decisive source
```ts
// Intl.NumberFormat renders negatives with U+2212 MINUS SIGN in 36 locales
// (sv, fi, nb, nn, hr, et, sl, lt, eu, fo, gsw, se, ksh), so copying one of
// our own cells and pasting it back dropped the sign. Normalize to ASCII '-'
// before the strips below, which treat U+2212 as noise.
value = value.replace(/\u2212/g, '-');
...
// Phase two — the strips above keep every '-', so the sign is resolved here,
// the same way extractDecimalFromString does it for the cell editor: a minus
// ahead of the digits is the sign ("-$1", "$-1"); any later one is noise
// ("100-50" -> 10050).
const isNegative = cleanedValue.startsWith('-');
cleanedValue = cleanedValue.replace(/-/g, '');
```

**Flow:** normalize typographic minus FIRST (locale formatters emit it for negatives — normalization before strip means one rule covers all locales and the currency path too) → strip non-[digits·separator·'-'] → resolve sign LAST from leading-minus position → Number(). The OLD code stripped a mid-string '-' via `(?!^-)` lookaround inside the strip regex AND never normalized U+2212, so `$-99.5` worked but `-99.5` (U+2212) became 99.5.
**Invariant:** (1) Sign resolution must come AFTER all strips, keyed on "minus ahead of digits = sign, later minus = noise" — identical rule to extractDecimalFromString backing the cell editor, so paste and typing agree. (2) The en-US currency fast path must KEEP '-' (`[^0-9.-]`) because serializeDecimalValue resolves it downstream. (3) Empty cleaned value → null regardless of isNegative.
**Probe:** `packages/nocodb-sdk/src/lib/columnHelper/columns/Decimal.spec.ts:60` 'keeps a U+2212 minus sign', :67 '$-99.5'→-99.5, :71 '100-50'→10050; `utils/serializer.spec.ts:61/:206` U+2212 twins; `serializeIntValue` spec :256. DIRECT upstream tests present (jest specs).

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "serializeDecimalValue minus sign serializer", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt normalize-before-strip + resolve-after-strip ordering verbatim; adapt separator handling to host locales; omit Intl locale list (enumerate your own).
