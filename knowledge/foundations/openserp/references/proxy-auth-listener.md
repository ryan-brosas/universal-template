<!-- capsule-v2 -->
# CDP proxy-auth listener — how are proxy credentials injected into Chrome without --proxy-server creds, and why does it fight HijackRequests?

**Source:** OpenSERP MIT `main@29c7b0fb`; Codebase Memory `ext-aeo-openserp`. **Question:** How is a persistent Fetch auth handler installed safely, and what must resource blocking give up under it?

## Launch-flag split + persistent listener
**Path/Symbol:** `core/browser.go:NewBrowser` (L305–332), `startProxyAuthListener` (L478–560), `proxyAuthFetchPatterns` (L169–182), `configureRequestBlocking` (L184–237).
**Signature:** `proxyURLForBrowserLaunch(u *url.URL) string` (strips userinfo/path/query, socks5h→socks5); `startProxyAuthListener(browser *rod.Browser) error`.
**Data Shape:** Fetch patterns limited to http/https Document requests at Request stage.

### Decisive source
```go
// Chrome's --proxy-server flag must NOT include credentials; strip them and
// re-inject via a persistent CDP Fetch.handleAuthRequired listener installed
// after each connect.
l = l.Proxy(proxyStr); b.proxyUser = ...; b.proxyPass = ...
...
wait := scoped.EachEvent(
	func(e *proto.FetchAuthRequired) bool {
		go func(requestID proto.FetchRequestID) {   // concurrent acks:
		// sequential dispatch becomes the bottleneck — Chrome times out paused
		// requests faster than we ack → "Invalid InterceptionId", stalled navs.
			proto.FetchContinueWithAuth{...Credentials...}.Call(scoped)
		}(e.RequestID); return false },
	func(e *proto.FetchRequestPaused) bool { go continueRequest; return false },
)
close(started)          // handlers installed BEFORE FetchEnable — no race
<-started
proto.FetchEnable{Patterns: ..., HandleAuthRequests: true}.Call(browser)
// configureRequestBlocking:
if b.proxyUser != "" { return nil } // HijackRequests' page-level Fetch.enable
                                    // collides with the browser-level one →
                                    // "Invalid InterceptionId"; tracker blocking
                                    // via NetworkSetBlockedURLs still works (not Fetch-based).
```

**Flow:** on reconnect the previous listener is cancelled and joined (authCancel/authStopped) before installing a new one; IgnoreCertErrors(true) accompanies proxy/insecure so MITM proxies work; router goroutine stopped on ctx done to avoid goroutine leak.
**Invariant:** exactly ONE owner of the Fetch domain per browser session; acks for distinct RequestIDs are independent ⇒ safe to parallelize; auth listener lifetime = connection lifetime, not request lifetime.
**Probe:** `go test ./core -run 'TestProxyPerContext|TestBrowserResourceBlocking'` + proxy_integration_test.go (tag-gated live Chrome).
**Probe executed (real runner):** the written pattern matches ZERO tests (names live inside other suites) — repaired: `TestShouldBlockResourceType` (core, 1 PASS: document/main_frame always fetched, fonts/media blocked) and `TestProxyAuthFetchPatternsOnlyInterceptDocuments` (1 PASS: Fetch patterns intercept documents only). Tag-gated live-Chrome integration tests remain skipped by design.
**Python-equivalent probe (executed):**
```bash
grep -n 'HijackRequests\|HandleAuthRequests\|Invalid InterceptionId\|close(started)' core/browser.go | head -6
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-openserp", query: "startProxyAuthListener FetchContinueWithAuth proxyURLForBrowserLaunch configureRequestBlocking", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the strip-then-reinject credential pattern and install-before-enable ordering; adapt if your driver offers native proxy auth; omit resource-type blocking entirely when an auth listener owns Fetch (tracker URL blocking survives).
