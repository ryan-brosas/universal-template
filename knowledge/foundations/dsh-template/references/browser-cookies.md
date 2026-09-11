<!-- capsule-v2 -->
# Browser cookies — dump the active tab's cookies

**Source:** dsh-template (no LICENSE, `pi-fovea-foundation@ffb36822ffbcbba509deebaf3ea9412a9ea8b2c4`); Codebase Memory `dsh-template`. **Question:** How does a CDP browser script dump the active tab's cookies (name, value, domain, path, httpOnly, secure) in a readable format?

## Dump active-tab cookies
**Path/Symbol:** `.dsh/skills/pack-frontend/browser-tools/browser-cookies.js` (whole file, 36 lines); the connect race (6–16), the last-tab guard (18–23), the cookie dump (25–34).
**Signature:** `node browser-cookies.js` → prints each cookie's fields; exits 1 if the browser is unreachable or no active tab. Uses `puppeteer-core` `connect({ browserURL: "http://localhost:9222" })`.
**Data Shape:** `p = (await b.pages()).at(-1)`; `cookies = await p.cookies()` (an array of `{ name, value, domain, path, httpOnly, secure, ... }`).

### Decisive source
```js
const b = await Promise.race([
  puppeteer.connect({ browserURL: "http://localhost:9222", defaultViewport: null }),
  new Promise((_, reject) => setTimeout(() => reject(new Error("timeout")), 5000)),
]).catch((e) => { console.error("✗ Could not connect to browser:", e.message); process.exit(1); });

const p = (await b.pages()).at(-1);
if (!p) { console.error("✗ No active tab found"); process.exit(1); }

const cookies = await p.cookies();
for (const cookie of cookies) {
  console.log(`${cookie.name}: ${cookie.value}`);
  console.log(`  domain: ${cookie.domain}`);
  console.log(`  path: ${cookie.path}`);
  console.log(`  httpOnly: ${cookie.httpOnly}`);
  console.log(`  secure: ${cookie.secure}`);
  console.log("");
}
await b.disconnect();
```

**Flow:** (1) connect under a 5s race; (2) take the last tab (guard if none); (3) `p.cookies()`; (4) print each cookie's name/value/domain/path/httpOnly/secure; (5) disconnect.

**Invariant:** the last tab is the target; a missing tab exits 1 with a clear message; the cookie fields are printed fully (including the boolean httpOnly/secure).

**Probe:** no direct test file exists. Verified by direct source read (file indexed `no_recorded_issue` + `metadata_match`). The last-tab + `p.cookies()` dump is the executable contract.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dsh-template", query: "browser-cookies cookies httpOnly", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the bounded-connect + last-tab + `p.cookies()` dump. Adapt the connect URL to the host. Omit if cookie inspection is not needed.
