<!-- capsule-v2 -->
# Fingerprint profiles — how does a session get a coherent UA/locale/timezone/WebGL persona that matches the real binary?

**Source:** OpenSERP MIT `main@29c7b0fb`; Codebase Memory `ext-aeo-openserp`. **Question:** Which profile fields must be patched at runtime, and how do lanes keep cookies+persona sticky?

## Catalog selection & runtime patching
**Path/Symbol:** `core/browser/profile.go:SelectProfileForSessionHeadless/eligibleProfiles/pickWeighted/LaneKey` (L188–340), `core/browser.go:laneProfile/applyRuntimeBrowserVersionValues/applyProfile/profileDisplayMetricsFor` (L648–1042), lane store in `core/proxy_lane.go`.
**Signature:** `SelectProfileForSessionHeadless(engine, region, salt string, headless bool) Profile`; `applyRuntimeBrowserVersion(profile, browser)`.
**Data Shape:** embedded profiles.json: UA template with `{chrome_major}`, UACHBrands/UACHFullVerList, platform/platformVersion/arch/bitness/mobile, AcceptLanguage, NavigatorLangs, Locale, Timezone, Viewport, tags(linux/macos/windows, swiftshader), weight.

### Decisive source
```go
wantSwiftShader := headless && goos == "linux"     // Docker renders WebGL via SwiftShader;
	if slices.Contains(p.Tags, "swiftshader") != wantSwiftShader { continue }  // no WebGL spoofing
h := fnv.New32a(); h.Write([]byte(salt))            // stable-but-varied per session
idx := int(h.Sum32()) % total
// runtime truth beats catalog: version.Product tells Chrome vs Chromium/HeadlessChrome
fullVersion = extractChromeVersion(version.UserAgent)   // regex (?:Headless)?Chrome/x.y.z.w
profile.UserAgent = strings.ReplaceAll(template, "{chrome_major}", major)  // or rewrite
profile.UACHBrands = patchBrandVersions(..., major, false)  // Not_A Brand stays "24"
if product != "" && !strings.HasPrefix(product, "Chrome/") { removeChromeBrand(profile) }
// emulation set applied per PAGE (headless windows are fake):
NetworkSetUserAgentOverride{UserAgent, AcceptLanguage(navigator.tags), Platform, UserAgentMetadata}
EmulationSetLocaleOverride / EmulationSetTimezoneOverride
EmulationSetDeviceMetricsOverride{W,H, scale1, mobile, Screen*, Position*}
EmulationSetEmulatedMedia{prefers-reduced-motion:no-preference, color-scheme:light, forced-colors:none}
NetworkSetExtraHTTPHeaders{"Accept-Language": q-weighted header}
```
Lane stickiness: LaneStore keyed (tenant, engine, sessionID-or-sha16(proxy identity)); Profile() caches persona, Cookies() restores pre-nav via Network.setCookies, SaveCookies after nav, DropCookies on captcha challenge (resilient layer). applyProfileLanguageHint overrides locale fields only when the requested language differs — an explicit region isn't clobbered by defaults.

**Invariant:** headless Linux keeps ONLY the first navigator language (linux headless-shell limitation); setWindowBounds is skipped headless (can close the target; device metrics covers it); launch locale pinned en-US because speech voices are per-process.
**Probe:** `go test ./core/browser -run TestProfile` incl. profile_coherence_test.go (UA ↔ brands ↔ platform consistency).
**Probe executed (real runner):** `-run TestProfile` alone matches zero names — repaired: `go test ./core/browser -v` = **6/6 top-level PASS** incl. TestSelectProfile(+ForSession subtests), TestEligibleProfilesMatchRuntimePlatform, TestEligibleProfilesHeadlessLinuxUsesSwiftShader, TestProfileNavigatorLanguages*, TestApplyProfileLanguageHint(RewritesTimezone); the coherence suite runs as table-driven subtests inside TestProfileCoherence in the same green run.
**Python-equivalent probe (executed):**
```python
import re
ua="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/146.0.0.0 Safari/537.36"
m=re.search(r'(?:HeadlessChrome|Chrome)/(\d+\.\d+\.\d+\.\d+)',ua)
assert m and m.group(1).startswith('146')
print("version extraction GREEN:", m.group(1))
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-openserp", query: "SelectProfileForSessionHeadless pickWeighted applyRuntimeBrowserVersion applyProfile LaneStore restoreLaneCookies", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt catalog+salt selection, runtime-major patching, and the full CDP emulation set (partial emulation is what gets you flagged); extend profiles.json for your fleet's GPUs; omit mobile personas unless you also change SERP layouts.
