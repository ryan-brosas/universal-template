<!-- capsule-v2 -->
# Protocol codegen — how do 652 typed wrappers stay drift-free against upstream Chrome?

**Source:** browser-harness-js MIT `main@6b189406`; Codebase Memory `browser-harness-js`. **Question:** What is the generation contract that turns `browser_protocol.json` + `js_protocol.json` into `generated.ts`, and what must a porter not hand-edit?

## Vendored JSONs → namespaces + Domains interface + bindDomains factory, redirects skipped
**Path/Symbol:** `skills/cdp/sdk/gen.ts` (`loadDomains` :63-71, `jsdocLines` :80-87, `renderType` :90-120, `build` :168-274); output `generated.ts` (15,160L, `bindDomains` at :14391-15158).
**Signature:** `node gen.ts` (top-level await script) → writes `generated.ts`: `Transport { _call(method, params?): Promise<unknown> }`, per-domain type namespaces, `<Cmd>Params`/`<Cmd>Return` interfaces, the `Domains` interface of method signatures, and `bindDomains(t: Transport): Domains`.
**Data Shape:** `$ref` with a dot resolves qualified as-is; bare `$ref` becomes `CurrentDomain.<Type>` (unqualified refs are domain-local); enums → string-literal unions; `binary` → base64 `string`; `any` → `unknown`. Anonymous nested `object` properties render as INLINE object-literal types (`renderObject` :122-129, object without properties → `Record<string, unknown>` :113-115). Protocol descriptions embed as JSDoc with every `*/` escaped to `*\/` (`jsdocLines` :80-87) — without that escape a single upstream description containing a comment closer would terminate the generated JSDoc block and break `generated.ts` compilation.

### Decisive source
```ts
function jsdocLines(text: string | undefined, indent: string): string {
  if (!text) return '';
  // Escape `*/` so it doesn't close the JSDoc block early.
  const safe = text.replace(/\*\//g, '*\\/');
```
```ts
const realCmds = d.commands.filter(c => !c.redirect);   // redirected commands: canonical version lives in the target domain
...
out.push(`      ${escId(c.name)}: (params?: any) => t._call(${JSON.stringify(fq)}, params) as any,`);
...
const paramSig = noParams ? `()`
  : allOpt ? `(params?: ${d.domain}.${capName}Params)`
  : `(params: ${d.domain}.${capName}Params)`;           // all-optional params make the OBJECT itself optional
```
with reserved-word escaping via `escId` (JSON-stringified identifiers like `"new"` still render valid TS property names).

**Flow:** read both vendored protocol JSONs → sort domains alphabetically → emit type namespaces (object types as interfaces, enum strings as unions) → emit Params/Return interfaces per non-redirected command (namespace merging makes the two blocks one) → emit the `Domains` interface with JSDoc'd signatures → emit `bindDomains` mapping every method to `t._call('Domain.method', params)` → footer stats line for sanity.
**Invariant:** (1) `generated.ts` is NEVER hand-edited — swap the JSONs and re-run `node gen.ts`, then restart the daemon to reload bindings. (2) Events are deliberately NOT generated (commands only); experimental/deprecated ARE included. (3) Redirected commands are dropped so each wire method has exactly one canonical wrapper. (4) The whole SDK's typing hinges on `Session implements Transport` — `_call`'s signature IS the public contract.
**Probe:** no test runs codegen; determinism probe = run `node gen.ts` twice, diff outputs (must be identical), or verify the stats footer count against `grep -c 't._call' generated.ts` → 652 (the footer's command figure). CAUTION: `grep -c ': (params' generated.ts` returns 1150 — it ALSO hits every Params/Return interface signature line — and can never match the footer (erratum from pass-4 audit: this dead-end verification shipped as the stated method). Description-safety pin (pass 7): `grep -n "close the JSDoc block early" skills/cdp/sdk/gen.ts` → :82. Graph retrieval pins `generated.bindDomains @ generated.ts:14391-15158`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness-js", query: "bindDomains", limit: 3, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the vendored-schema→typed-facade codegen shape for any protocol SDK you want zero-drift; adapt type mappings ($ref scoping especially) to your schema dialect; omit nothing here without replacing the redirect-skip rule — keeping both spellings of a redirected command is how double-dispatch bugs are born.
