<!-- capsule-v2 -->
# Response handling & server-driven control plane — how do status codes, HX-* headers, and htmx:beforeSwap mutate what happens?

**Source:** htmx MIT `master@ad56dff71e55d9c717447437b4c942a64575d4b2` (v2.0.10); Codebase Memory `ext-htmx`. **Question:** How does the response-handling table decide swap/error, and which response headers override or retarget the client's plan — in what precedence order?

## resolveResponseHandling + handleAjaxResponse: config table then header overrides
**Path/Symbol:** `src/htmx.js:resolveResponseHandling` (:4754-4766) + `codeMatches` (:4745-4748); header control flow `handleAjaxResponse` (:4804-4971) with retarget resolution `resolveRetarget` (:4788-4798); history decision `determineHistoryUpdates` (:4663-4738).
**Signature:** `function codeMatches(responseHandlingConfig, status)` → `new RegExp(config.code).test(status.toString(10))`; default table: `[{code:'204',swap:false},{code:'[23]..',swap:true},{code:'[45]..',swap:false,error:true}]`.
**Data Shape:** Each entry: `{code, swap, error?, ignoreTitle?, select?, target?, swapOverride?, event?}`. First matching entry wins; NO match ⇒ `{swap:false}` (silent no-op).

### Decisive source
```js
if (hasHeader(xhr, /HX-Retarget:/i)) { responseInfo.target = resolveRetarget(elt, xhr.getResponseHeader('HX-Retarget')) }
if (hasHeader(xhr, /HX-Reswap:/i))  { swapOverride = xhr.getResponseHeader('HX-Reswap') }
...
var beforeSwapDetails = mergeObjects({ shouldSwap, serverResponse, isError, ignoreTitle, selectOverride, swapOverride }, responseInfo)
if (responseHandling.event && !triggerEvent(target, responseHandling.event, beforeSwapDetails)) return
if (!triggerEvent(target, 'htmx:beforeSwap', beforeSwapDetails)) return
target = beforeSwapDetails.target             // listeners may re-target
serverResponse = beforeSwapDetails.serverResponse // ...replace content
isError = beforeSwapDetails.isError           // ...flip error/success classification
```

**Flow:** HX-Trigger fired BEFORE anything else (events during load) → HX-Location (client-side redirect; JSON form carries full swap context; defaults push:true) → HX-Redirect (+HX-Refresh) short-circuit with `keepIndicators=true` so spinners survive navigation → history update decision → status-table resolution → config-entry target/swap/select/event applied → HX-Retarget / HX-Reswap / HX-Reselect OVERRIDE the table → htmx:beforeSwap veto/mutation → swap pipeline with afterSwap/afterSettle callbacks firing HX-Trigger-After-Swap/-Settle (re-targeted to body if elt died).
**Invariant:** Retarget resolution THROWS on unresolvable selectors (`resolveRetarget` fires `htmx:targetError` then throws 'Invalid re-target') — a server bug surfaces as an exception, not a silent body replacement; `target:'this'` means the requesting element. Status 286 is special-cased inside shouldSwap: it cancels polling (see trigger-dispatch-fsm). Error events fire only for entries flagged `error:true` — swapping error content and raising htmx:responseError are independent axes.
**Invariant (history):** precedence is HX-Push ≻ HX-Push-Url ≻ HX-Replace-Url ≻ hx-push-url/hx-replace-url attrs ≻ boosted default push of responsePath||requestPath; value `'false'` cancels, `'true'` follows responsePath||requestPath; anchors re-attach when absent.

**Probe:** Table behavior pinned by `test/core/config.js`: "swaps normally with no config update" :12, "swap all config should swap everything" :49 (`{code:'...',swap:true}`), "non mapped responseHandling config will not swap" :93, per-field override tests target/swap/select/title/error/event :119-288. Header ladder: `test/core/headers.js` HX-Retarget :261, "override back to this" :272, invalid-retarget error :283, HX-Reswap :303, HX-Reselect :312, unset variant :322, HX-Trigger-After-Swap/Settle :332/:366, HX-Location JSON :400, HX-Refresh :463, HX-Redirect :474. History precedence: `test/attributes/hx-push-url.js:336` HX-Push, :352 HX-Push-Url, :368 `false` ignored. 400-default-no-swap boundary at `test/core/ajax.js:892`.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-htmx", query: "responseHandling code matches status swap error", limit: 4 });
```
(rank-1 `src.htmx.codeMatches src/htmx.js 4745-4748`)

## Verdict
Adopt the two-layer model (declarative status table + imperative header/event overrides) and the throw-on-bad-retarget stance. Adapt the regex-code matching to your language (it deliberately accepts `[23]..` style patterns). Omit HX-Location's client-side redirect plane if your server controls navigation out of band. Coverage caveat: verified against test blocks at pin; runner not executed.
