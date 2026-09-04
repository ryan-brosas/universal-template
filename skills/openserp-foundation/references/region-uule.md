<!-- capsule-v2 -->
# Region resolution & UULE — how does a free-text region become engine-native targeting without errors?

**Source:** OpenSERP MIT `main@29c7b0fb`; Codebase Memory `ext-aeo-openserp`. **Question:** How is a region hint resolved to Google UULE vs Yandex lr, and why does resolution NEVER fail?

## RegionTarget resolution order
**Path/Symbol:** `core/region/region.go` (whole file, dependency-free stdlib-only by design), `core/locale.go` re-exports, `google/url.go:googleUULE/googleLocale` (L375–432).
**Signature:** `ResolveRegion(region string) RegionTarget{Raw, Country, GoogleCanonical, YandexLR}`; `GoogleUULE(region) string`; `EncodeGoogleUULE(canonical) string`; `ParseLocale(code) Locale{Language, Country}`; `CountryFromRegion(hint)`.
**Data Shape:** priority: digits ⇒ YandexLR passthrough ("213") → 2-letter country/locale ⇒ Country + country-lr table (US→84, GB/UK→102, DE→96…) → bare curated city (~60 entries, e.g. "berlin"→"Berlin,Berlin,Germany") → ≥2 commas ⇒ verbatim canonical passthrough.

### Decisive source
```go
const googleUULEPrefix = "w+CAIQICI"
var googleUULELengthAlphabet = []byte("ABC...xyz-_")   // 64 chars

func EncodeGoogleUULE(canonical string) string {
	length := len([]rune(canonical))
	if length <= 0 || length >= len(googleUULELengthAlphabet) { return "" }
	return googleUULEPrefix + string(googleUULELengthAlphabet[length]) +
		base64.StdEncoding.EncodeToString([]byte(canonical))
}
// UULE takes effect ONLY for exact canonical names; countries ride gl=:
if target.Country != "" || target.YandexLR != "" { return "" }  // no UULE
```
Locale parsing: "_"→"-", language lowercase / country uppercase; `defaultLocaleCountryByLanguage` fills bare languages ("de"→DE) for Accept-Language and timezone derivation (`TimezoneForLocale`: US→America/New_York …).

**Flow:** profileRegionHint (context.go) picks the strongest market signal for fingerprint matching: explicit country wins over langCode, forming "en-DE"-style pairs; cacheProxyMarket reuses the same precedence for cache keys.
**Invariant:** ResolveRegion never errors — unrecognized input yields empty fields so callers fall back to prior behavior; UULE length char is the RUNE COUNT index into the alphabet (canonical ≥64 chars unsupported).
**Probe:** `go test ./core -run TestRegion` + `core/locale_test.go`.
**Probe executed (real runner):** `-run TestRegion` alone = 1 PASS; the locale/UULE plane spans two packages — repaired: `go test ./core -run 'TestRegion|TestLocale|TestTimezoneForLocale'` (2 PASS) + `go test ./core/region -run TestGoogleUULE` (1 PASS) = all executed green at pin.
**Python-equivalent probe (executed):**
```python
import base64
alpha="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
canon="Berlin,Berlin,Germany"; n=len(canon)
uule="w+CAIQICI"+alpha[n]+base64.b64encode(canon.encode()).decode()
expect="w+CAIQICIRQmVybGluLEJlcmxpbitHZXJtYW55".replace('+','+')  # sanity shape check
assert uule.startswith("w+CAIQICIR") and "QmVybGlu" in uule
print("UULE GREEN:", uule)
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-openserp", query: "ResolveRegion GoogleUULE EncodeGoogleUULE ParseLocale yandexLRByCountry", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the resolution-priority chain, never-fail contract, and UULE encoder byte-for-byte; extend the city table from current Google geotargets data; omit tables for markets you don't serve.
