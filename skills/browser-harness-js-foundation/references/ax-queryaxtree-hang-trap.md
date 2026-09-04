<!-- capsule-v2 -->
# ax-queryaxtree-hang-trap — why does queryAXTree hang through the explicit-sessionId shim while getFullAXTree works on both paths?

**Source:** browser-harness-js MIT `main@6b1894061e7a09a65a974d7d65a210b9a7ef06e0`; Codebase Memory `browser-harness-js`. **Question:** Which invocation path must queryAXTree use so it doesn't hang forever?

## Session-path requirement for queryAXTree
**Path/Symbol:** `skills/cdp/interaction-skills/accessibility-tree.md` "Prefer `queryAXTree`" (:5–11) + Traps (:145–151); contrast with ax-locator-resolution.md's 3s-race fallback.
**Signature:** `await session.use(targetId); await session.Accessibility.queryAXTree({ nodeId, role?, accessibleName? })`.
**Data Shape:** TWO hard requirements: (1) a node anchor is REQUIRED — bare `{role, accessibleName}` errors with "Either nodeId, backendNodeId or objectId must be specified." (pass the document root to query the whole page); (2) call on the ACTIVE session after `session.use(targetId)` — routing through the `cdp(sessionId, "Accessibility.queryAXTree", …)` shim HANGS (no response, no error).

### Decisive source
```md
- **`queryAXTree` hangs on the `cdp(sessionId, …)` path.** Routing it through
  the explicit-sessionId shim (`cdp(sessionId, "Accessibility.queryAXTree", …)`)
  does not return. Call it on the active session: `session.use(targetId)` then
  `session.Accessibility.queryAXTree(…)`. `getFullAXTree` does not have this
  issue and works via either path.
```

**Flow:** session.use(targetId) → DOM.getDocument → queryAXTree({nodeId: root.nodeId, role, accessibleName}) → filter `!n.ignored` → bridge to coordinates via `DOM.getBoxModel({backendNodeId})` (`model.border[0..1]` = top-left; center = x+w/2, y+h/2).
**Invariant:** queryAXTree returns ALL matches (not first) and ignored nodes too — always `nodes.find(n => !n.ignored)` and disambiguate multiples by properties/subtree/index-after-screenshot. `backendDOMNodeId` can be undefined for virtual nodes — check before getBoxModel. getFullAXTree on giant pages can exceed the WS per-message limit and close the socket ("CDP socket closed") — scope with getPartialAXTree/queryAXTree instead (the general WS-limit contract of payload-limits-replay).
**Probe:** `grep -cF 'must be specified' skills/cdp/interaction-skills/accessibility-tree.md` → 1; `grep -cF 'that path hangs' <same>` → 1; `grep -cF '`getFullAXTree` does not have this issue' <same>` → 1; `grep -cF 'exceed the WS per-message limit and close the connection' <same>` → 1; `grep -c 'nodes.find(n => !n.ignored)' <same>` → 3.
**Retrieve:** search_graph --project browser-harness-js --query "queryAXTree" resolves the generated.ts typed wrapper (line-exact) — pair with search_code --pattern "accessibility-tree" for the doctrine Module.

## Verdict
Adopt active-session-only routing for queryAXTree + the always-filter-ignored + box-model-center bridge. Adapt disambiguation heuristics per site. Omit getRootAXNode/getChildAXNodes walks unless you need enable-gated tree traversal (see ax-domain-enable-matrix).
