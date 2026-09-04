<!-- capsule-v2 -->
# Browser lifecycle — how is one long-lived Chrome kept healthy across thousands of scrapes?

**Source:** OpenSERP MIT `main@29c7b0fb`; Codebase Memory `ext-aeo-openserp`. **Question:** Why must rod's browser.Timeout never be set here, and what's the teardown order that avoids spurious "target closed" errors?

## Connection hygiene
**Path/Symbol:** `core/browser.go:newRodBrowser` (L436–448 comment block), `ensureConnectedBrowser` (L562–602), `Navigate` (L1282–1407), `ClosePageWithTimeout/closeOnErr` (L1323–1334, L1470–1499).
**Signature:** `Navigate(ctx, URL) (*rod.Page, error)`; `ensureConnectedBrowser(ctx, forceReconnect bool)`.
**Data Shape:** healthPingTimeout 3s, healthPingSkipWindow 5s; BrowserOpts defaults Timeout 30s, WaitLoadTime 2s.

### Decisive source
```go
// Do NOT set browser.Timeout: it bakes connectTime+d into the connection's
// context. The connection is persistent, so after d every call (including the
// Version() health ping) fails with "context deadline exceeded", forcing a
// reconnect on every Navigate and orphaning pages ("Session with given id not
// found"). Per-operation timeouts live at call sites instead.
return rod.New().NoDefaultDevice().ControlURL(b.browserAddr)
...
if !state.lastOK.IsZero() && time.Since(state.lastOK) < healthPingSkipWindow {
	return state.browser, nil                       // skip ping when recently OK
}
pingCtx,_ := context.WithTimeout(...); state.browser.Context(pingCtx).Version()
// teardown ORDER matters:
closeOnErr := func() {
	stopNetworkUsageWatcher(page)
	page.Close()                                     // page FIRST,
	disposeBrowserContext(browser, browserContextID) // then context — reversing
}                                                // makes Chrome kill the target first
                                                  // → spurious "target closed" on Close.
```

**Flow:** ensureConnected (ping or skip) → IgnoreCertErrors under proxy/insecure → createIsolatedPage (TargetCreateBrowserContext with optional per-context proxy; dispose context on ANY later failure) → lane profile select + applyProfile → restoreLaneCookies → configureRequestBlocking → start watchers (main-document status via Network.responseReceived; optional network byte usage) → timedPage.Navigate → classifyProxyNetworkError wraps nav failures → WaitLoad timeout treated NON-fatal (DOM may already be usable) → statusWatcher.Status maps 403→ErrBlocked / 429→ErrRateLimited → saveLaneCookies.
**Invariant:** every early-exit path runs closeOnErr/stopWatchersOnErr (watchers leak goroutines even when LeavePageOpen keeps tabs); single-shot force-reconnect on stale websocket sessions; ClosePageWithTimeout bounds shutdown closes with a fresh Background-based ctx (a cancelled request ctx would make cleanup impossible).
**Probe:** `go test ./core -run 'TestBrowser'` (browser_test/browser_unit_test cover ping-skip window and teardown); integration tests need Chrome.
**Probe executed (real runner):** `-run 'TestBrowser'` alone matches only 3 tests; the profile plane lives in `core/browser` — full `go test ./core/browser -v` = **6/6 top-level PASS** incl TestSelectProfile(ForSession) lane subtests and the coherence suite at pin.
**Python-equivalent probe (executed):**
```bash
grep -n 'healthPingSkipWindow\|closeOnErr()\|disposeBrowserContext' core/browser.go | head -8
grep -n 'Do NOT set browser.Timeout' core/browser.go
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-openserp", query: "ensureConnectedBrowser createIsolatedPage ClosePageWithTimeout DeferClosePage mainDocumentStatusWatcher", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt persistent-connection hygiene (no baked deadlines, ping-with-skip-window, ordered teardown, bounded closes); adapt timeouts to your scrape latency; omit LeavePageOpen debug affordances in production.
