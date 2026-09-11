<!-- capsule-v2 -->
# hyperscript adapter — what does the compiler-free `h` package inject, and how does its JSX runtime differ from React's?

**Source:** SolidJS solid MIT `main@f47845f9cc16ecbb316aa6560c7161f45af9a3d8`; Codebase Memory `solid`. **Question:** Which DOM operations must a host supply so tagged-template hyperscript works without the Solid compiler, and what does `jsx(type, props)` actually call?

## Connected graph-selected seam
**Path/Symbol:** `packages/solid/h/src/index.ts:h` (:12–19); `packages/solid/h/src/hyperscript.ts:1`; `packages/solid/h/jsx-runtime/src/index.ts:jsx` (:9–11), `Fragment` (:5–7), export line (:14).
**Signature:** `h: HyperScript = createHyperScript({ spread, assign, insert, createComponent, dynamicProperty, SVGElements })`; `function jsx(type: any, props: any) { return h(type, props); }`.
**Data Shape:** six injected members from `solid-js/web`: three insertion ops (`spread`, `assign`, `insert`), one component gate (`createComponent`), one prop-coercion op (`dynamicProperty`), and the SVG tag-name set. `hyperscript.ts` body is exactly `export * from "hyper-dom-expressions";` — all template machinery is EXTERNAL.

### Decisive source
```ts
// h/src/index.ts — the entire in-repo surface
const h: HyperScript = createHyperScript({
  spread,
  assign,
  insert,
  createComponent,
  dynamicProperty,
  SVGElements
});
export default h;
```
```ts
// h/jsx-runtime/src/index.ts — React-transform compatibility by aliasing
function jsx(type: any, props: any) { return h(type, props); }
// support React Transform in case someone really wants it for some reason
export { jsx, jsx as jsxs, jsx as jsxDEV, Fragment };
```

**Flow:** host supplies the six web operations → `createHyperScript` (external) closes over them and returns the `HyperScript` callable usable both as `h\`<div>...\`` template tag and direct call → the optional JSX runtime routes every transform call through that single `h`, with `jsxs`/`jsxDEV` as pure aliases and `Fragment(props)` = `props.children`.
**Invariant:** because `jsx === jsxs === jsxDEV`, there is no static-children distinction (React's `jsxs` optimization does not exist here) — children arrays are handled identically; anything the tagged templates need (spreading, dynamic property coercion, SVG namespace decisions via `SVGElements`) comes exclusively from the injected ops.
**Probe:** graph evidence: name-pattern retrieval on `^(h|jsx|jsxs|jsxDEV|Fragment)$` over `packages/solid/h/*` returns exactly `h` Variable :12–19 (in-degree 3), `jsx` Function :9–11, `Fragment` Function :5–7; direct reads of the three files pin the bodies. No test spec exists under `h/` — coverage caveat: claims rest on direct source reads.

## Get live surrounding code
**Retrieve:** BM25 query `"createHyperScript spread assign insert dynamicProperty"` scoped to `packages/solid/h/*` returns 0 hits (package too token-poor) — honest miss; use the executed fallback:
```ts
await mcp.codebase_memory.search_graph({ project: "solid", name_pattern: "^(h|jsx|jsxs|jsxDEV|Fragment)$", file_pattern: "packages/solid/h/*", limit: 10 });
```

## Verdict
Adopt the six-op injection contract as the definition of "host" for any compiler-free renderer, and the single-`h` JSX aliasing trick for React-transform interop. Adapt op implementations to your DOM layer. Omit porting `hyper-dom-expressions` itself — same external boundary class as dom-expressions (recorded in leaf Boundaries).
