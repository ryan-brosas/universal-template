<!-- capsule-v2 -->
# UA profile record — what fields make ONE coherent UA/device profile record?

**Source:** itbrowser-net/undetectable-fingerprint-browser no-LICENSE `main@6df77401149f82fa089589946859a92a0d9f6bb7`; Codebase Memory `undetectable-fingerprint-browser`. **Question:** Which fields must travel together so a generated navigator/device plane passes coherence checks?

## Record schema of user-agents.json
**Path/Symbol:** `fingerprints/user-agents.json`:2–22 (record 1); graph Variables `fingerprints.user-agents.*` (19 keys incl. connection subkeys).
**Signature:** `Array<{appName, connection?, language, platform, pluginsLength, screenWidth, screenHeight, userAgent, vendor, viewportWidth, viewportHeight, weight, deviceCategory, oscpu?}>`.
**Data Shape:** 10,000 records; always-present core (12 fields); `connection` present on 4,118 records with subkeys downlink, downlinkMax?, effectiveType, rtt, type? (Network Information API optionality preserved); `oscpu` only on Gecko profiles.

### Decisive source
```json
{
  "appName": "Netscape",
  "connection": { "downlink": 10, "downlinkMax": 100, "effectiveType": "4g", "rtt": 100, "type": "cellular" },
  "language": "en-US",
  "platform": "Linux armv81",
  "pluginsLength": 0,
  "screenHeight": 984,
  "screenWidth": 432,
  "userAgent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
  "vendor": "Google Inc.",
  "viewportHeight": 858,
  "viewportWidth": 432,
  "weight": 0.0006144760863064296,
  "deviceCategory": "mobile"
}
```
Executed probes: `jq -r 'map(keys[]) | unique | join(", ")'` → 14-key union; Gecko gating:
`oscpu:"Linux x86_64"` co-occurs with `vendor:""` and `rv:125.0) Gecko` UA (probed pass 1).

**Flow:** pick record → set navigator UA/platform/vendor/language (+`oscpu` iff Gecko) → apply screen/viewport pair → pluginsLength → optionally expose `connection` members → deviceCategory routes mobile indicators (touch, UA-CH mobile form factors).
**Invariant:** engine-conditional fields gate TOGETHER: `oscpu` ⇔ empty `vendor` ⇔ Gecko UA token; Chromium profiles never carry `oscpu`. `deviceCategory` must agree with platform family (iPhone/iPad/armv81 ⇒ mobile/tablet).
**Probe:** `jq '[.[] | select(has("oscpu"))][0].vendor' fingerprints/user-agents.json` → `""` pins the Gecko gate (executed pass 1).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "undetectable-fingerprint-browser", label: "Variable", file_pattern: "user-agents.json", limit: 25 });
```

## Verdict
Adopt the field set, optionality pattern (connection members may be individually absent), and engine gating; adapt key naming to your injection layer; omit synthesizing new field values — capture real pairs instead (see viewport caveat in weighted-profile-sampling). Coverage caveat: schema derived from full-table jq census of the pinned file, not from producer code.
