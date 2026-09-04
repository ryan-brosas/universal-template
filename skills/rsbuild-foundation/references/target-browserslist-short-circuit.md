<!-- capsule-v2 -->
# target + browserslist short-circuit — why does the default browserslist compile to es2017 and web-worker lose browserslist support?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must reproduce the target string synthesis and its es-query optimization.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/plugins/target.ts` whole 4–38; DEFAULT_WEB_BROWSERSLIST in constants.ts; tests `packages/core/tests/target.test.ts` case table.
**Signature:** modifyBundlerChain order:'pre' handler keyed on target.
**Data Shape:** chain.target(string | [string, esQuery]); esQuery = 'es2017' | `browserslist:${list.join(',')}`.

### Decisive source
```ts
if (target === 'node') { chain.target('node'); return; }   // node ignores browserslists entirely
const isDefaultBrowserslist = browserslist.join(',') === DEFAULT_WEB_BROWSERSLIST.join(',');
if (target === 'web-worker') {
  // TODO: Rspack should support `browserslist:` for webworker target
  chain.target(isDefaultBrowserslist ? ['webworker','es2017'] : ['webworker','es5']);
  return;
}
const esQuery = isDefaultBrowserslist ? 'es2017' : (`browserslist:${browserslist.join(',')}` as const);
chain.target(['web', esQuery]);
```

**Flow:** comparing JOINED strings (not array identity) because normalization may clone arrays. The default path emits a bare ES-level instead of a browserslist query — rspack resolves es-features directly, skipping browserslist parsing on every module. Custom lists ride the `browserslist:` query so SWC applies @babel/preset-env-compatible target mapping.
**Invariant:** (1) web-worker with custom browserslist degrades to es5 — surprising but pinned upstream (rspack limitation TODO); (2) 'pre' ordering matters: later plugins read chain.target() to branch (isWebTarget etc.); (3) node must not receive an es query or server builds downlevel needlessly.
**Probe:** unit `packages/core/tests/target.test.ts` case table {node→'node', custom-list→['web','browserslist:Chrome 100'], default→['web','es2017'], worker→['webworker',...]}.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "pluginTarget DEFAULT_WEB_BROWSERSLIST isDefaultBrowserslist", limit: 8 });
```

## Verdict
Adopt joined-string default detection and es-level short-circuit. Adapt default list to host support matrix. Re-check the worker TODO before porting past this pin.
