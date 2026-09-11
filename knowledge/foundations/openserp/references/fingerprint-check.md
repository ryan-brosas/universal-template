<!-- capsule-v2 -->
# Fingerprint self-check harness — how does the repo verify its own anti-detection posture against detector sites?

**Source:** OpenSERP MIT `main@29c7b0fb`; Codebase Memory `ext-aeo-openserp`. **Question:** What is the Detector SPI and how do debug endpoints expose it safely?

## fpcheck runner
**Path/Symbol:** `core/fpcheck/runner.go` (whole file), `core/fpcheck/detectors/registry.go` (whole file), endpoint `core/server.go:handleFingerprintCheck` (L723–864, EnableDebugEndpoints-gated).
**Signature:** `RunWithOptions(ctx, browser BrowserNavigator, detector Detector, RunOptions{ArtifactDir, WaitBeforeExtract, WaitBeforeClose}) (Report, error)`.
**Data Shape:** Report{detector_name, url, detections map[name]Detection{detected, severity, details}, summary{passed, failed, critical[]}, raw_notes, screenshot, captured_at_utc}; standard detectors sannysoft/rebrowser/browserscan/pixelscan/deviceandbrowser + custom(url,selector).

### Decisive source
```go
page, err := browser.Navigate(ctx, detector.URL())
defer func() { ...closePageWithTimeout(context.Background(), ...) }()  // Background: cleanup must run even if ctx cancelled
detections, rawNotes, err := detector.Extract(ctx, page)
if err != nil { _ = saveScreenshot(page, screenshotPath); return report, err } // evidence on failure
summary.Failed++ / summary.Critical when severity == "critical"
```
Endpoint param ladder: detector=all|name|custom (custom REQUIRES url; forces insecure default true since arbitrary sites have cert variety); headless=false ignored without DISPLAY (warn+force headless); timeout_ms default 150000; X-Proxy-URL honored under AllowRequestProxyURL but authenticated SOCKS rejected (browser runtime).
**Invariant:** detectors run SEQUENTIALLY on one fresh debug browser (closed via defer); screenshots always attempted — a failed extraction still leaves artifacts; the route is disabled unless EnableDebugEndpoints (never ship open fingerprint probing).
**Probe:** `go test ./core -run TestDebugFingerprint` (server_test.go pins disabled-by-default and each 400 validation branch).
**Probe executed (real runner):** same command at pin = **6 PASS** (disabled-by-default, wait/detector param validation, custom-detector URL/insecure/required branches); detector SPI suites `./core/fpcheck/detectors` = **5 PASS** whole-package.
**Python-equivalent probe (executed):**
```bash
grep -n 'EnableDebugEndpoints\|IsCustom\|DISPLAY' core/server.go | head -6
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-openserp", query: "fpcheck RunWithOptions detectors SelectWithCustomSelector handleFingerprintCheck", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the Detector SPI + artifact-on-failure pattern for your own anti-detect CI; rotate detector-site selectors constantly (diagnostic-only code); omit the HTTP surface entirely in production deployments.
