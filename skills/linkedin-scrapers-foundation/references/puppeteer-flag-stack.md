<!-- capsule-v2 -->
# Puppeteer flag stack — which Chromium launch flags make headless scraping survive containers (and which are cargo cult)?

**Source:** linkedin-profile-scraper-api MIT `master@9fc7125`; Codebase Memory `linkedin-profile-scraper-api`. **Question:** Which launch flags are load-bearing when running headless Chrome for scrapes — and does this stack double as anti-detection?

## The 47-flag args array
**Path/Symbol:** `src/index.ts:LinkedInProfileScraper.setup` (:218–269) — `args:` passed to `puppeteer.launch`.
**Signature:** `puppeteer.launch({ headless: boolean, args: string[], timeout: number })`; first arg is spread-conditional: `...(headless ? '---single-process' : '---start-maximized')`.
**Data Shape:** one flat string array; `timeout` reused for both launch and every navigation.

### Decisive source
```ts
...(this.options.headless ? '---single-process' : '---start-maximized'), // NOTE: triple-dash typo upstream; Chromium silently ignores it
'--no-sandbox',
'--disable-setuid-sandbox',
"--proxy-server='direct://",
'--proxy-bypass-list=*',
'--disable-dev-shm-usage',
'--disable-web-security',
'--enable-automation',        // ← the OPPOSITE of stealth
// ... ~40 more disable-* hygiene flags
```

**Flow:** launch → `setup()` immediately calls `checkIfLoggedIn()` (:273) so a mis-launched or cookie-dead browser fails at the auth probe, not mid-scrape; any launch error routes through `close()` (:278) so a half-started Chrome cannot leak.
**Invariant:** the container-critical quartet is `--no-sandbox` + `--disable-setuid-sandbox` (running as root/in containers), `"--proxy-server='direct://"` + `--proxy-bypass-list=*` (forces DIRECT connections, defeating system proxies that break CDP traffic — note the embedded quote is part of the upstream value), and `--disable-dev-shm-usage` (prevents `/dev/shm` exhaustion on small containers). CRITICAL negative finding: this stack is NOT a stealth stack — it explicitly ships `--enable-automation` and `--disable-web-security`. Its evasion budget is spent on UA string + cookie auth instead. Do not confuse it with the suite's `browser-fingerprint-stealth` trio.
**Probe:** no test launches a browser — source-grounded only. Cross-check against `browser-fingerprint-stealth.md` before porting flags for stealth purposes.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-profile-scraper-api", query: "setup puppeteer launch args no-sandbox", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the container quartet (`--no-sandbox`, `--disable-setuid-sandbox`, forced-direct proxy pair, `--disable-dev-shm-usage`) as a portable floor plus the fail-fast-at-auth-probe wiring. Adapt per environment. Omit blind wholesale copying: `--enable-automation` actively fights fingerprint-evasion goals, and the leading `'---single-process'` is a silent no-op typo — evidence that these lists accrete, not that each flag was chosen.
