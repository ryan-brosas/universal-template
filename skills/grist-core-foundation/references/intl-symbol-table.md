<!-- capsule-v2 -->
# Intl-derived number symbol table — how do you parse locale-formatted numbers ("1.234,56", "€ 1,00-") without a regex zoo per locale?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** Where does the canonical set of separators/symbols for parsing come from, and which parts of the format are probed at runtime?

## Constructor interrogates Intl.NumberFormat.formatToParts(-1234567.5678) across four NumModes
**Path/Symbol:** `app/common/NumberParse.ts`: `class NumberParse` (:45), constructor probing (:77–133), public symbol fields (:57–68), `getDigitsMap` (:24–35).
**Signature:** `new NumberParse(locale: string, currency: string)`; entry point `NumberParse.fromSettings(docSettings, options?)`.
**Data Shape:** Public readonly: `currencySymbol, percentageSymbol, exponentSeparator, minusSign, decimalSeparator, digitGroupSeparator, digitGroupSeparatorCurrency, currencyEndsInMinusSign: boolean, defaultNumDecimalsCurrency, digitsMap: Map<localeDigit→ascii>`.

### Decisive source
```ts
for (const numMode of NumMode.values) {           // decimal | currency | percent | scientific
  const formatter = Intl.NumberFormat(locale, parseNumMode(numMode, currency));
  const formatParts = formatter.formatToParts(-1234567.5678);
  parts.set(numMode, formatParts);
}
...
this.currencySymbol = getPart("currency", "currency");
this.percentageSymbol = getPart("percentSign", "percent");
this.exponentSeparator = getPart("exponentSeparator", "scientific");
this.minusSign = getPart("minusSign");
this.decimalSeparator = getPart("decimal");
this.digitGroupSeparator = getPart("group");      // checked against BOTH but never "which is in use"
this.digitGroupSeparatorCurrency = getPart("group", "currency");
this.currencyEndsInMinusSign = last(parts.get("currency"))!.type === "minusSign";
```

**Flow:** Format one sentinel value (-1234567.5678) per mode → read part values by type → derive two derived facts: trailing-minus currencies (`"€ 1,00-"`, tested by last-part type) and the currency's default fraction digits (length of the `"fraction"` part). Non-ASCII locales get a digits map (e.g. Arabic-Indic → 0-9) built by formatting 0..9.
**Invariant:** The runtime platform (ICU) is the single source of truth — no hardcoded separator tables to drift per locale. A porter hardcoding "." and "," breaks half the world. Two group separators are accepted simultaneously on parse but never distinguished (deliberate laxness, see digit-group-laxness). `defaultNumDecimalsCurrency` later decides whether an explicit `decimals: 0` option must be forced to suppress `$1.00`-style defaults (see format-option-voting).
**Probe:** `bash -c 'cd /mnt/hdd/utopia/inspo/platforms/grist-core && grep -n "formatToParts(-1234567.5678)" app/common/NumberParse.ts && grep -n "getDigitsMap(locale)" app/common/NumberParse.ts'` → :81 and :126.
Direct tests: `test/common/NumberParse.ts` :8 `describe("NumberParse")`; :279 parametrized `with ${locale.code} locale` matrix over many locales.

### Retrieve
```bash
codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"NumberParse locale currency formatToParts digitGroupSeparator","limit":5,"detail":"ids"}'
```

## Verdict
Adopt the formatToParts-probing constructor wholesale — it is the portability core; adapt sentinel value/mode list if your host lacks Intl (then you own the tables); omit the digitsMap only for ASCII-only deployments.
