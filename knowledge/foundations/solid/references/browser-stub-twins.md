<!-- capsule-v2 -->
# browser stub twins — how does isomorphic code importing SSR render functions survive a client bundle?

**Source:** SolidJS solid MIT `main@f47845f9cc16ecbb316aa6560c7161f45af9a3d8`; Codebase Memory `solid`. **Question:** What should `renderToString`/`renderToStream` and the `ssr*` template helpers DO when they end up in a browser bundle — throw, no-op, or something in between?

## Connected graph-selected seam
**Path/Symbol:** `packages/solid/web/src/server-mock.ts:throwInBrowser` (:2–6), `renderToString` (:8–16), `renderToStringAsync` (:17–26), `renderToStream` (:27–40), `ssr*` family (:41–58), deprecated `pipeTo*` (:59–85).
**Signature:** stubs keep the EXACT client-visible signatures of the real server exports (same options objects: `nonce`, `renderId`, `timeoutMs`, `onCompleteShell/All`, pipe targets) so TypeScript consumers cannot tell them apart.
**Data Shape:** render fns return `undefined` (typed as `string`/`Promise<string>`/stream object — the file is `//@ts-nocheck`); every `ssr*` helper returns an empty shape (`{ t: string }` / `string`) matching what compiled JSX-SSR call-sites expect to thread around.

### Decisive source
```ts
function throwInBrowser(func: Function) {
  const err = new Error(`${func.name} is not supported in the browser, returning undefined`);
  console.error(err);                       // fail-SOFT: log, never throw
}

export function ssr(template: string[] | string, ...nodes: any[]): { t: string } {}
export function ssrElement(name, props, children, needsId): { t: string } {}
```

**Flow:** bundler resolves the browser condition of `solid-js/web` to this module → shared components whose compiled output calls `ssr(...)`/`ssrElement(...)` keep executing harmlessly (empty `{t}` nodes) → if app code actually invokes a render function in the browser, it logs the named error and returns undefined instead of crashing the bundle.
**Invariant:** signature parity with the real server plane (including deprecated `pipeToWritable`/`pipeToNodeWritable` typed stubs) + fail-soft semantics: the only observable behavior of a mis-routed render call is one `console.error` and an `undefined` result. The `ssr*` no-op family exists precisely because compiled SSR primitives appear inside components that also run client-side during hydration.
**Probe:** `packages/solid/web/test/server-mock.spec.tsx` — three tests pin, for each render fn: `mockConsoleError.mock.calls[0][0].message` contains `"<name> is not supported in the browser, returning undefined"` AND `result === undefined`. Wired via `export * from "./server-mock.js"` in `web/src/index.ts:34`.

## Get live surrounding code
**Retrieve:** executed BM25 query `"renderToString renderToStream not supported in the browser"` ranks `throwInBrowser` :2–6 first, then `renderToString` :8–16 and `renderToStream` :27–40.
```ts
await mcp.codebase_memory.search_graph({ project: "solid", query: "renderToString renderToStream not supported in the browser", limit: 10 });
```

## Verdict
Adopt fail-soft named-error stubs with exact signature parity for any server-only API that can be imported from shared/isomorphic modules. Adapt error text and logging channel. Omit throwing — upstream deliberately chose log-and-return-undefined; a throw here breaks hydration bundles that merely touch these exports.
