<!-- capsule-v2 -->
# Capability negotiation matrix — what does each side promise when declaring `capabilities`, and what must the other side do about it?

**Source:** modelcontextprotocol/specification MIT `main@4df2d6b6e3588efb46e7542d98498e5c630a0a86` (`schema/draft/schema.ts` identical except doc-link paths); Codebase Memory `modelcontextprotocol`. **Question:** When I add a feature to my MCP server or client, exactly which capability key must I declare, and how does the peer behave when it's present vs absent?

## Capabilities are presence-typed promises, not configuration
**Path/Symbol:** `schema/2026-07-28/schema.ts:ClientCapabilities` (:716–786) and `schema/2026-07-28/schema.ts:ServerCapabilities` (:793–883).
**Signature:** `interface ClientCapabilities { experimental?, roots?, sampling?: {context?, tools?}, elicitation?: {form?, url?}, extensions?: {[key]: JSONObject} }` / `interface ServerCapabilities { experimental?, logging?, completions?, prompts?: {listChanged?}, resources?: {subscribe?, listChanged?}, tools?: {listChanged?}, extensions? }`.
**Data Shape:** Every key optional; mere PRESENCE of a key = "I support this protocol surface" (empty object `{}` = baseline support with no settings). Sub-keys refine sub-features (`sampling.tools`, `elicitation.form|url`, `resources.subscribe|listChanged`). `experimental` and `extensions` are open string-keyed `JSONObject` maps; extension keys MUST follow `_meta` prefixed naming rules (e.g. `"io.modelcontextprotocol/tasks"`).

### Decisive source
```ts
// ClientCapabilities (:716-786)
export interface ClientCapabilities {
  experimental?: { [key: string]: JSONObject };
  /** Present if the client supports listing roots.
   * @deprecated Deprecated as of protocol version 2026-07-28 (SEP-2577). */
  roots?: {};
  /** Present if the client supports sampling from an LLM.
   * @deprecated Deprecated as of protocol version 2026-07-28 (SEP-2577). */
  sampling?: {
    context?: JSONObject;  // includeContext support
    tools?: JSONObject;    // tools + toolChoice support
  };
  elicitation?: { form?: JSONObject; url?: JSONObject };
  extensions?: { [key: string]: JSONObject }; // keys follow _meta naming rules
}
// ServerCapabilities (:793-883)
export interface ServerCapabilities {
  logging?: JSONObject;    // @deprecated SEP-2577
  completions?: JSONObject;
  prompts?:   { listChanged?: boolean };
  resources?: { subscribe?: boolean; listChanged?: boolean };
  tools?:     { listChanged?: boolean };
  extensions?: { [key: string]: JSONObject };
}
// :789 — "this is not a closed set: any server can define its own, additional capabilities."
```

**Flow:** Declaration TIMING is asymmetric: SERVER capabilities are declared once, at construction/handshake time (the reference server constructs `McpServer` with its capabilities before any request — see `conditional-tool-registration`), while CLIENT capabilities are re-declared PER REQUEST under `io.modelcontextprotocol/clientCapabilities`. A server consults `clientCapabilities` BEFORE issuing a server→client request: no `elicitation` key ⇒ never call `elicitation/create`; `sampling` without `tools` ⇒ no tool-use loop inside sampling. A client consults `serverCapabilities` before calling surfaces: no `resources.subscribe` ⇒ don't open subscription listen streams; no `prompts.listChanged` ⇒ don't expect list-changed notifications. Presence checks are PRESENCE, not truthiness: `caps.roots !== undefined` against a `|| {}`-defaulted object — an empty-object sub-capability like `roots?: {}` is falsy in JS yet MEANS supported, so truthiness checks misclassify baseline capabilities.
**Invariant:** Presence-is-support, absence-is-never-call. Declaring a sub-capability you can't honor breaks the peer; calling an undeclared surface is a spec violation on the caller side. Unknown keys are legal (open set) — forward-compatible peers ignore them rather than reject. Never cache client capabilities across requests (statelessness — see `meta-key-grammar`).
**Probe:** No direct test runner ships in this repo (docs/spec repo). Deterministic probe: `grep -n 'roots?: {}' schema/draft/schema.ts` pins the deprecated empty-object presence form; `diff schema/draft/schema.ts schema/2026-07-28/schema.ts` shows only doc-link differences, so ranges hold for both revisions. Coverage: `check_index_coverage` → all four cited paths `no_recorded_issue` + `metadata_match`.

## Get live surrounding code
**Retrieve:** The graph indexes functions but not bare schema interfaces in this project — retrieve the generator that renders these interfaces into published schemas, then read the file directly:
```bash
codebase-memory-mcp cli search_graph --project modelcontextprotocol \
  --query 'validateSchemaExamples generateSchema' --detail ids --limit 5
# → scripts/validate-examples.ts, scripts/generate-schemas.ts; then:
sed -n '716,883p' schema/2026-07-28/schema.ts
```

## Verdict
Adopt the presence-typed negotiation shape (empty-object baseline, sub-key refinement, open extension maps with `_meta`-prefixed keys) for any MCP-compatible handshake; adopt the gating discipline (check before call) in clients/servers alike. Adapt capability objects to your transport's discovery mechanism if not JSON-RPC. Omit `sampling`/`roots`/`logging` declarations in new implementations (deprecated SEP-2577 — legacy interop only). Caveat: this repo has no test suite pinning behavior; claims rest on schema source + prose pages.
