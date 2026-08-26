<!-- capsule-v2 -->
# Browser eval — evaluate arbitrary JS in the page and format the result

**Source:** dsh-template (no LICENSE, `pi-fovea-foundation@ffb36822ffbcbba509deebaf3ea9412a9ea8b2c4`); Codebase Memory `dsh-template`. **Question:** How does a CDP browser script evaluate an arbitrary expression in the page (including async), and print the result in a readable shape whether it is a scalar, an array of objects, or a plain object?

## Evaluate JS in the page
**Path/Symbol:** `.dsh/skills/pack-frontend/browser-tools/browser-eval.js` (whole file, 54 lines); arg join (6), the connect race (15–25), `p.evaluate` with `AsyncFunction` (34–37), result formatting (39–52).
**Signature:** `node browser-eval.js 'code'` → prints the result; exits 1 if no code or the browser is unreachable. Uses `puppeteer-core` `connect({ browserURL: "http://localhost:9222" })`.
**Data Shape:** `code = process.argv.slice(2).join(" ")` (so unquoted multi-word expressions work). Evaluates via `p.evaluate((c) => new AsyncFunction(\`return (${c})\`)())`, which supports both sync and async expressions.

### Decisive source
```js
const code = process.argv.slice(2).join(" ");
const b = await Promise.race([
  puppeteer.connect({ browserURL: "http://localhost:9222", defaultViewport: null }),
  new Promise((_, reject) => setTimeout(() => reject(new Error("timeout")), 5000)),
]).catch((e) => { console.error("✗ Could not connect to browser:", e.message); process.exit(1); });

const p = (await b.pages()).at(-1);
if (!p) { console.error("✗ No active tab found"); process.exit(1); }

const result = await p.evaluate((c) => {
  const AsyncFunction = (async () => {}).constructor;
  return new AsyncFunction(`return (${c})`)();
}, code);

// Format: array of objects -> one block per element; object -> key: value lines; else scalar
if (Array.isArray(result)) {
  for (let i = 0; i < result.length; i++) {
    if (i > 0) console.log("");
    for (const [key, value] of Object.entries(result[i])) console.log(`${key}: ${value}`);
  }
} else if (typeof result === "object" && result !== null) {
  for (const [key, value] of Object.entries(result)) console.log(`${key}: ${value}`);
} else {
  console.log(result);
}
await b.disconnect();
```

**Flow:** (1) join args into a code string; (2) connect under a 5s race; (3) take the last tab; (4) `p.evaluate` with an `AsyncFunction` wrapper so both sync and async expressions resolve; (5) format the result (array-of-objects → per-element blocks, plain object → `key: value` lines, else scalar); (6) disconnect.

**Invariant:** the `AsyncFunction` wrapper makes the evaluated expression awaitable (async support); the last tab is the target; result formatting never crashes on arrays/objects/scalars.

**Probe:** no direct test file exists. Verified by direct source read (file indexed `no_recorded_issue` + `metadata_match`). The `AsyncFunction` eval and the three-way result formatter are the executable contract.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dsh-template", query: "browser-eval AsyncFunction evaluate", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the `AsyncFunction`-wrapped `page.evaluate` (async-capable), the last-tab target, and the array/object/scalar result formatter. Adapt the connect URL to the host. Omit if a headless runner is preferred.
