<!-- capsule-v2 -->
# Stable AX locators — how do you reference an element across snapshot rebuilds when `[n]` refs die with each `getFullAXTree`?

**Source:** browser-harness-js MIT `main@6b189406`; Codebase Memory `browser-harness-js`. **Question:** What locator grammar survives re-snapshots, and what is the resolution ladder when the fast path hangs?

## role:R["N"] grammar → queryAXTree raced 3s → full-tree scan fallback
**Path/Symbol:** `skills/cdp/sdk/helpers.ts:parseLocator` (:53-87), `isLocatorString` (:89-91), `resolveLocator` (:93-133); emitted by `axview.ts:axView({locators:true})` (`loc=role:` + `JSON.stringify(name)`, :301).
**Signature:** `parseLocator(loc: string): { role: string; name?: string }` (accepts optional `loc=` prefix) · `resolveLocator(loc: string): Promise<number>` (returns `backendDOMNodeId`) · `isLocatorString(ref): boolean` (`'loc='` or `'role:'` prefix).
**Data Shape:** locator = `role:<role>` optionally followed by `["<accessibleName>"]`; names are JSON-stringified so embedded quotes survive round-trips.

### Decisive source
```ts
const { nodes } = await Promise.race([
  session.domains.Accessibility.queryAXTree(params),   // cheap, scoped — but HANGS on some Chromium builds
  new Promise<never>((_, rej) => setTimeout(() => rej(new Error('queryAXTree timeout')), 3_000)),
]);
const node = (nodes || []).find((n: any) => !n.ignored && n.backendDOMNodeId);
...
// Fallback: scan the full AX tree ... reliable when the served build doesn't answer queryAXTree.
const node = (all || []).find((n: any) => {
  if (n.ignored || !n.backendDOMNodeId) return false;
  const r = n.role && n.role.value;
  if (!r || r.toLowerCase() !== role.toLowerCase()) return false;
  ...
});
```
The hand-written scanner is deliberately BACKSLASH-FREE (Set-based char classes via `String.fromCharCode`) so the file can travel through transports that choke on regex-literal escapes.

**Flow:** parse grammar → fast path: `DOM.getDocument` root + `queryAXTree({nodeId, role, accessibleName?})`, raced against a hard 3s timer → first non-ignored node with a `backendDOMNodeId` wins → on timeout/error fall through to a whole-tree `getFullAXTree` scan comparing role case-insensitively and exact name → miss throws with the scan size in the message.
**Invariant:** (1) `[n]` refs are valid for exactly ONE `getFullAXTree` call; locators (role+name) resolve against live state and therefore survive navigation/mutation — multi-step loops must carry locators, not refs. (2) The race is not optional decoration: the same hang the docs warn about for the `cdp(sid,…)` route also bites the active-session call on some builds; without the 3s cap every locator miss would cost a hang. (3) `ignored` nodes must be filtered at BOTH paths; virtual nodes may lack `backendDOMNodeId`.
**Probe:** direct tests `skills/cdp/sdk/axview.test.ts` pin the emitted grammar round-trip (:62-110 incl. quotes-in-names via `JSON.stringify`). Resolution ladder source-pinned: `grep -n "queryAXTree timeout\|getFullAXTree" skills/cdp/sdk/helpers.ts` (:107, :117).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness-js", query: "resolveLocator", limit: 3, fields: ["signature", "name", "file"] });
// resolves helpers.resolveLocator @ helpers.ts:93-133
```

## Verdict
Adopt the role+name locator grammar and the raced-fast-path/fallback ladder wherever you expose "act on element X" to an LLM across mutating pages; adapt the 3s budget; omit the full-tree fallback only if your Chrome build provably answers `queryAXTree`. Keep names JSON.stringify'd — hand-escaping quotes is the bug the tests exist to prevent.
