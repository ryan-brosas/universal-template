<!-- capsule-v2 -->
# Navigator scalar cohorts — frozen compat constants, alignment laws WITH their true scope, and the anomaly twins

**Source:** itbrowser-net/undetectable-fingerprint-browser no-LICENSE `main@6df77401149f82fa089589946859a92a0d9f6bb7`; Codebase Memory `undetectable-fingerprint-browser`. **Question:** Which `navigator` fields are frozen compatibility shims, and how far does cross-field version alignment actually hold?

## Path/Symbol
**Path/Symbol:** `fingerprints/fingerprints.db.xz` → `.navigator{}` (13 keys: app_codename, app_name, app_version, brands, full_version, full_version_list?, pdf_viewer_enabled, platform, product, product_sub, user_agent, vendor, vendor_sub). Graph caveat: `not_tracked` artifact; plane absent from node surface (Retrieve → total 0).

## Signature
**Signature:** `.navigator.user_agent` is an INTEGER INDEX (0..219, product-private vocabulary); the UA string itself appears only inside `.app_version`.

## Data Shape
- **SIX byte-constants ×10000** (violation count 0): `app_codename "Mozilla"`, `app_name "Netscape"`, `product "Gecko"`, `product_sub "20030107"`, `vendor "Google Inc."`, `vendor_sub ""`.
- `pdf_viewer_enabled` is a real minority cohort `{true×9946, false×54}`.
- `full_version_list` present on ALL records whose surface was checked (missing count 0).
- **UA-string truncation (pass-7 refinement):** only **99/10000** records carry a full UA with a `Chrome/<major>` token in `.app_version`; the other 9901 truncate at `"5.0 (Windows NT 10.0; Win64; x64) AppleWebKit"`. On those 99: UA major == full_version major (0 violations) AND == every Chrome|Edg brand major (0 violations).
- **Corpus-wide brand law WITH its true scope (pass-7 refinement):** over the 9998 branded non-empty-full_version records, Chrome|Edg brand majors equal full_version majors EXCEPT exactly **10 mismatch records** (e.g., full_version 118 with brand "Google Chrome" v114/v108) — real captured drift a consistency checker must TOLERATE, not hard-fail.
- **Anomaly twins ×2:** empty-brands `[]` AND empty `full_version:""` (same byte-duplicate pair; ua_idx 108 class). Any corpus-wide major arithmetic MUST guard non-empty strings or jq dies on them.

### Decisive source
```jsonc
// fresh pass-7 stream probes (verbatim)
constants violations : 0
rich-UA records      : 99 ; ua-vs-fv mismatches 0 ; ua-vs-brand mismatches 0
brand-vs-fv corpus   : {"brand_fv_mismatch":10}   // of 9998 guarded records
anatomy              : {"empty_fv":2,"empty_brands":2}
pv cohort            : pdf_viewer_enabled==false -> 54
major spectrum       : {"min":7,"max":121}
```

**Flow:** copy scalars verbatim → align brand/full_version majors from the SAME record → treat the 10-record mismatch family and the 2 anomaly twins as valid cohorts when validating, never as corruption to repair.
**Invariant:** the compat shim sextet NEVER varies; version alignment is strong-but-not-absolute (9988/9998 clean); a validator that requires perfect alignment rejects real captured profiles.

**Probe:** `xz -dc fingerprints/fingerprints.db.xz | jq -c '[.[] | select(.navigator.app_codename!="Mozilla" or .navigator.app_name!="Netscape" or .navigator.product!="Gecko" or .navigator.product_sub!="20030107" or .navigator.vendor!="Google Inc." or .navigator.vendor_sub!="")] | length'` → `0` (executed pass 7); mismatch probe `{brand_fv_mismatch:[.[] | select(.navigator.full_version != "") | {fv:(.navigator.full_version|split(".")[0]|tonumber), b:[.navigator.brands[] | select((.brand|test("Chrome|Edg"))) | .version|tonumber]} | . as $r | select(any($r.b[]; . != $r.fv))] | length}` → `10` (executed pass 7).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "undetectable-fingerprint-browser",
  query: "hardware_concurrency device_memory do_not_track pdf_viewer_enabled vendor product_sub constants" });
// executed pass 7 -> total: 0 (plane absent from node surface; this capsule is the only path)
```

## Verdict
Adopt the frozen shim values, the scoped alignment laws, and anomaly tolerance; adapt field naming per host API; omit asserting perfect corpus-wide alignment (refined by execution this pass). Caveat: user_agent index resolves outside the repo (index-indirection).
