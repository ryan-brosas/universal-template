<!-- capsule-v2 -->
# Learnings registry — how do you codify per-site recipes as callable tools instead of re-deriving selectors every call?

**Source:** browser-harness-js MIT `main@6b189406`; Codebase Memory `browser-harness-js`. **Question:** What is the manifest contract that lets an agent call `learnings(domain, tool, args)` for both Node-side and page-side tools?

## nodeTools via dynamic import with ctx injection; browserTools via Runtime.evaluate source concatenation
**Path/Symbol:** `skills/cdp/sdk/helpers.ts:loadManifest` (:228-234), `ctxForTool` (:236-243), `learnings` (:245-277), `listLearnings` (:214-226); layout contract `skills/cdp/learnings/README.md`; reference fixture `learnings/example/manifest.json` + `tools/get-outline.mjs`.
**Signature:** `listLearnings(): Promise<string[]>` (dirs WITH a parseable manifest.json, sorted) · `learnings(domain: string, tool?: string, args?: unknown): Promise<unknown>`.
**Data Shape:** `manifest.json`: `{id, name, domains?, notes?, nodeTools?: {<name>: {description, path, callable, args?, returns?}}, browserTools?: {…same}}`; paths relative to the domain dir; node tool = ESM named export called as `fn(ctx, args)`.

### Decisive source
```ts
// nodeTool path — real module, real import, loud failure names the exports found:
const fn = mod ? mod[nodeDecl.callable] : undefined;
if (typeof fn !== 'function') {
  throw new Error('learnings: "' + tool + '" expected export "' + nodeDecl.callable + '" from ' + nodeDecl.path + '; found: ' + ...);
}
return await fn(ctxForTool(), args);

// browserTool path — the FILE SOURCE is wrapped and evaluated IN THE PAGE:
const src = await readFile(join(LEARNINGS_DIR, domain, brDecl.path), 'utf8');
const expr = '(async function(args){ ' + src + '; return typeof ' + brDecl.callable + ' === \'function\' ? await (' + brDecl.callable + ')(args) : ' + brDecl.callable + '; })(' + JSON.stringify(args ?? {}) + ')';
```
with `ctxForTool()` handing the tool EVERY REPL global (`session`, `cdp`, `axView`, `axClick`, `drainSignals`, `pageInfo`, …) so one function can compose snapshot→act→verify.

**Flow:** no-tool call returns `{nodeTools: keys, browserTools: keys, notes}` (a capability menu) → named tool resolves nodeTool FIRST (dynamic `import(pathToFileURL(...))`) else browserTool (read source → wrap → `Runtime.evaluate` with `returnByValue:true, awaitPromise:true`, exceptionDetails surfaced) → undeclared name throws listing what IS declared.
**Invariant:** (1) The split is RUNTIME, not style: nodeTools run in the daemon process (can loop, use fs, compose many CDP calls); browserTools run in the page (carry cookies/origin — see reverse-engineer-api recipe). Choosing wrong silently breaks auth context. (2) Errors are diagnostic-first: missing manifest vs bad JSON vs missing export vs undeclared tool each produce distinct messages naming paths/exports. (3) `args` cross the boundary ONLY as a JSON.stringify'd literal.
**Probe:** no direct test; the shipped fixture IS the executable spec — `skills/cdp/learnings/example/tools/get-outline.mjs` (18L: evaluate h2 texts, exceptionDetails surfaced, JSON.parse of in-page stringify). Deterministic probe: `grep -n "nodeTools\|browserTools" skills/cdp/sdk/helpers.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness-js", query: "learnings", limit: 3, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-runtime registry shape for any agent framework that accumulates site-specific know-how; adapt the manifest schema to your loader; omit browserTools if your threat model forbids shipping eval-strings — then keep nodeTools only and route page work through explicit CDP calls.
