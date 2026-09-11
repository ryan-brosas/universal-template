<!-- capsule-v2 -->
# Response-interception extraction — how do I get structured data from LinkedIn's SPA without fragile DOM parsing?

**Source:** linvo-scraper MIT `main@cfbe91080c7347591dee44a26f55d74bba734da2` (`LinkedinSalesPageService.pagesTask` :33–85); login-token capture `linkedin.login.service.ts` (:41–46). Codebase Memory `linvo-scraper`. **Question:** how do I intercept the network response (or its embedded `<code>` island) that already contains the data, instead of scraping rendered cards?

## waitForResponse with dual content-type predicate
**Path/Symbol:** `lib/linkedin/linkedin.sales.page.service.ts:pagesTask` — the waitForResponse block (:33–61) and the JSON-vs-HTML-`<code>` decode (:63–85).
**Signature:** `page.waitForResponse(predicate, { timeout: 0 })`; predicate inspects `p.headers()["content-type"]` AND body substrings; fallback decodes via in-page DOM.
**Data Shape:** two legal payloads — (a) `application/json` containing `firstName`+`elements`, (b) `text/html` whose `<code>` islands embed the same JSON; decoded to `{paging:{total}, elements:[…]}`.

### Decisive source
```typescript
const res = await page.waitForResponse(async (p) => {
    const text = await p.text();
    return (p.headers()["content-type"] === "application/json" &&
            text.indexOf("firstName") > -1 && text.indexOf("elements") > -1) ||
           (p.headers()["content-type"] === "text/html" &&
            text.split("<code").some(f =>
                ["firstName","elements","premium","degree","summary","entityUrn"]
                  .every(k => f.indexOf(k) > -1)));
}, { timeout: 0 });                                   // wait forever — navigation IS the trigger

const json = res.headers()["content-type"] === "application/json"
    ? await res.json()
    : await page.evaluate((val) => {                   // in-page: pick LAST matching <code> island
        const findElements = Array.from(div.querySelectorAll("code"))
          ?.filter(a => a?.textContent?.indexOf("elements")! > -1 && …firstName…);
        return JSON.parse(findElements[findElements.length - 1]?.textContent?.trim()!);
      }, txt);
```

**Flow:** navigate → SPA fires XHR(s) → predicate consumes each candidate response body (cheap substring gate before any parse) → on match decode by content-type → hand `{paging, elements}` straight to mapping (see profile-schema.md) → same trick captures session state: `page.cookies()` then `.find(t => t.name === "li_at")` for the auth token.
**Invariant:** the predicate must read the body ONCE (`p.text()` buffers it) and match on marker substrings BEFORE JSON-parsing — non-matching responses must not throw; HTML fallback takes the LAST matching `<code>` because LinkedIn appends updated views. Predicate errors are caught and return false so a broken response never kills navigation.
**Probe:** repo has no test suite (`lib/test.example.ts` is a placeholder) — coverage caveat recorded; graph resolves `LinkedinSalesPageService.pagesTask` and `salesNavChooser`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linvo-scraper", query: "pagesTask", limit: 5 });
```

## Verdict
Adopt substring-gated response interception with the JSON/`<code>`-island dual decoder and cookie-name token capture; adapt markers per endpoint and add your own timeouts (upstream uses 0 = infinite); omit Puppeteer-specific typing when porting to Playwright (`page.on("response")`). Caveat: source-grounded only.
