<!-- capsule-v2 -->
# Browser run race heptathlon — what seven concurrent watchers supervise one browser job, and who wins?

**Source:** growchief AGPL-3.0 `main@abb1e37a`; Codebase Memory `growchief`. **Question:** an automation promise can hang forever on a misbehaving page; which independent watchers race it and with what outcomes?

## Promise.race over six + outer Promise.any heartbeat
**Path/Symbol:** `shared/server/bots/bot.manager.ts:runProcess` (:579-651 main race; :531-546 pre-race); helpers `shared/server/bots/bot.tools.ts` (`_navigateOutSideOfScope` :69-99, `_checkForLoginElement` :132-157, `_maximumJobTime` :115-129, `_isProxyUnavailable` :37-67, `_functionToRun` :160-191).
**Signature:** `Promise.race<[ProgressResponse | 'logout' | false | 'proxy' | {picture,name,id} | {type:'ui-error',...}]>([...])`.
**Data Shape:** each watcher resolves to a discriminated outcome; `false` = automation failed silently; `'logout'/'proxy'` sentinels drive post-race branching (:710-716 proxy ⇒ delay 30min + repeat WITHOUT saving storage).

### Decisive source
```ts
race = await Promise.race([
  functionName !== 'login'
    ? this._navigateOutSideOfScope(page, findProvider.initialPage) // 1 scope escape
    : new Promise((res) => {}),
  functionName === 'screenShare'
    ? new Promise<ProgressResponse>(async (res) => { await timer(300000); res({...}); })
    : this._functionToRun(() => run.bind(findProvider)({ page, cursor, data }, lead), ...), // 2 runner
  this._checkForLoginElement(functionName !== 'login', cursor.page,
    findProvider.disconnectedElement),                                            // 3 logout
  this._maximumJobTime(abortController.signal, MAXIMUM_PROCESS_TIME /*240s*/,
    { delay: 0, repeatJob: true, endWorkflow: false }),                           // 4 stuck
  this._isProxyUnavailable(page, findProvider.initialPage, proxy),                // 5 proxy
  this._findRestrictions({page, cursor, data},
    findProvider.accountLimited.bind(findProvider)),                              // 6 limits
]);
```

**Flow:** before the main race, lead resolution itself races the logout watcher (:531-546). Inside the race: scope watcher resolves when `url.origin.indexOf(initialUrl) === -1 && url.href !== 'about:blank'` (free-control jailbreak guard, timeout 0 = forever); logout poller loops `locator(disconnectedElement).first().waitFor({timeout:0})`; process timer fires at 240s returning repeatJob:true; proxy watcher combines an upfront `axios.get('https://example.com')` THROUGH the proxy (5s timeout, any failure ⇒ 'proxy') plus a live `requestfailed` listener on the initial URL; restriction poller re-runs `accountLimited(params)` every 5s until non-false.
**Invariant:** losers of the race are NEVER cancelled — every watcher either resolves (sentinel/ProgressResponse) or hangs intentionally; cleanup relies on the page close + `_unsubscribeAll`, not on rejecting losers. The runner is wrapped by `_functionToRun` so a THROW becomes an outcome ({delay:20000,repeatJob:true} while page alive; login⇒false / else⇒endWorkflow when closed), never an exception that skips state-saving.
**Probe:** no test runner upstream. Deterministic pins: `grep -n 'MAXIMUM_PROCESS_TIME\|MAXIMUM_NAVIGATION_TIME\|MAXIMUM_RUNNING_TIME' shared/server/bots/bot.manager.ts` → :31-33; `grep -n "requestfailed" shared/server/bots/bot.tools.ts` → :58.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "growchief", query: "_checkForLoginElement _isProxyUnavailable _navigateOutSideOfScope _findRestrictions", limit: 10 });
```

## Verdict
Adopt: sentinel-discriminated race supervision with never-cancelling watchers and throw-to-outcome wrapping. Adapt watcher set to your failure modes. Omit LinkedIn/X disconnected-element selectors and the example.com probe host.
