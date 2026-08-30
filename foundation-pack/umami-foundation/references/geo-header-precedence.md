<!-- capsule-v2 -->
# Geo resolution with CDN-header precedence — how do you enrich events with country/region/city while honoring edge-provider headers and falling back to MaxMind?

**Source:** umami v3.3.1 / MIT @ master`ca661c70`; Codebase Memory `ext-umami`. **Question:** When do you trust geo headers vs a local GeoLite database, and how are header values decoded safely?

## geo-header-precedence
**Path/Symbol:** `src/lib/detect.ts:PROVIDER_HEADERS :10-40, getLocation :87-134, getClientInfo :136-148`; region join `getRegionCode :47-53`.
**Signature:** `getLocation(ip, headers, skipHeaders) -> {country, region, city} | undefined`; provider table = [umami-cloud (CLOUD_MODE), cloudflare, vercel, cloudfront, edgeone] each {countryHeader, regionHeader, cityHeader}.
**Data Shape:** region normalized to `<COUNTRY>-<REGION>` ISO form; header bytes treated as latin1 then decoded to utf-8 (`decodeHeader`).

### Decisive source
```ts
if (!cleanIp || !ipaddr.isValid(cleanIp) || (await isLocalIp(cleanIp))) return null;
if (!skipHeaders && !process.env.SKIP_LOCATION_HEADERS) {
  for (const provider of PROVIDER_HEADERS) {
    const countryHeader = headers.get(provider.countryHeader);
    if (countryHeader) {                       // FIRST matching provider wins wholesale
      return { country: decodeHeader(countryHeader), region: getRegionCode(...), city: ... };
    }
  }
}
// fallback: maxmind.open(GeoLite2-City.mmdb) memoized on globalThis[MAXMIND]
const country = result.country?.iso_code ?? result?.registered_country?.iso_code;
```

**Flow:** validate + exclude local IPs → provider headers (any single hit short-circuits ALL three fields from that provider) → MaxMind lookup with registered_country fallback → safeDecodeURIComponent applied by getClientInfo on the way out.
**Invariant:** `skipHeaders` is set when the payload itself supplied `ip` (tracker-declared IPs must not get edge geo — the headers describe the PROXY's view of the connection, not the claimed IP). Mixed provider fields are never merged: taking country from CF and city from Vercel would be silently wrong.
**Probe:** structural pins: `grep -c "cf-ipcountry\|x-vercel-ip-country\|cloudfront-viewer-country" src/lib/detect.ts` → ≥3 lines; `grep -n "registered_country" src/lib/detect.ts` → :130.
**Probe:** `grep -n "latin1" src/lib/detect.ts` → :57.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-umami", query: "getLocation PROVIDER_HEADERS maxmind decodeHeader", limit: 10 });
```

## Verdict
Adopt provider-table geo precedence with all-or-nothing field adoption; adapt the provider list to your edges; keep the skip-headers rule whenever callers may assert their own IP.
