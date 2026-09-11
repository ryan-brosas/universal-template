<!-- capsule-v2 -->
# Solid babel preset — how is JSX compilation delegated, and which built-ins escape component wrapping?

**Source:** SolidJS solid MIT `main@f47845f`; Codebase Memory `ext-solid`. **Question:** What does the preset configure, and why are the control-flow components listed as builtIns?

## babel-preset-solid/index.js: the whole compiler surface in-repo
**Path/Symbol:** `packages/babel-preset-solid/index.js` (whole file :1-34).
**Signature:** `module.exports = function (context, options = {}) { return { plugins: [[jsxTransform, {...defaults, ...options}]] }; }`.
**Data Shape:** the actual transform lives in the EXTERNAL `babel-plugin-jsx-dom-expressions` package; this repo pins its configuration: `moduleName: "solid-js/web"`, `generate: "dom"`, `contextToCustomElements: true`, `wrapConditionals: true`, and a 10-name builtIns list.

### Decisive source
```js
builtIns: [
    "For", "Show", "Switch", "Match", "Suspense",
    "SuspenseList", "Portal", "Index", "Dynamic", "ErrorBoundary"
],
```

**Flow:** user JSX → jsx-dom-expressions compiles `<Comp>` calls to `createComponent(Comp, props)` with GETTER-BASED props objects (`get children() { … }` — that's how laziness works without elements being functions), DOM tags to `template()`/`insert()`/`spread()` imports from solid-js/web, and expressions wrapped per wrapConditionals.
**Invariant:** The builtIns list exists because those identifiers must be treated as VALUES (imported bindings), not components to wrap — wrapping them would create a reactive boundary around what is already a primitive. A porter adding a new control-flow component MUST add it here or JSX will over-wrap it. Props-as-getters is the load-bearing convention: `createComponent` receives a props OBJECT whose properties re-enter tracking on each access — destructuring props breaks reactivity (the reason splitProps/mergeProps exist).
**Probe:** `grep -c 'babel-plugin-jsx-dom-expressions' packages/babel-preset-solid/index.js` → `1`. Behavior pinned by packages/babel-preset-solid/test.js (transform snapshots).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-solid", query: "babel-preset-solid builtIns moduleName generate", limit: 10 });
```

## Verdict
Adopt the config surface + getter-props convention. Adapt moduleName/generate ("dom"|"ssr"|"universal") per target. The transform itself is out-of-repo — treat it as an external dependency contract.
