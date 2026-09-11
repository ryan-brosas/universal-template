<!-- capsule-v2 -->
# Elicitation (create) — how does a server request structured or out-of-band info from a user through the client?

**Source:** modelcontextprotocol/specification MIT `main@4df2d6b`; Codebase Memory `modelcontextprotocol`. **Question:** What is the `elicitation/create` contract — form vs URL mode, the restricted JSON-schema subset, and the accept/decline/cancel response model?

## Two modes: form (in-band) and URL (out-of-band)
**Path/Symbol:** `docs/specification/draft/client/elicitation.mdx` (whole; overview :12–15; user interaction :17–47; capabilities :49–81; requests :83–102; form mode :104–320; URL mode :322–383; flows :385–432; response actions :434–467; implementation :469–671); wire types `schema/draft/schema.ts` (`ElicitRequestFormParams` :2788–2811, `ElicitRequestURLParams` :2821–2838, `ElicitRequestParams` :2845–2846, `ElicitRequest` :2856–2859, `PrimitiveSchemaDefinition` :2867–2868, `StringSchema` :2876–2884, `NumberSchema` :2892–2908, `BooleanSchema` :2916–2921, enum schemas :2931–3050+).

**Data Shape:** all elicitation requests MUST include `mode` (`"form"`/`"url"`, optional for form — defaults to `"form"`) and `message`. Form mode adds `requestedSchema` (a restricted JSON Schema). URL mode adds `url` (must be a valid URI).

**Capabilities:** clients supporting elicitation MUST declare `elicitation` in `_meta.io.modelcontextprotocol/clientCapabilities`. `{ "elicitation": { "form": {}, "url": {} } }` declares both; an empty object `{}` is equivalent to `{ "form": {} }` (form-only, backwards compat). Clients MUST support ≥1 mode; servers MUST NOT send requests with unsupported modes.

### Decisive source
```jsonc
// elicitation.mdx:355-374 (URL mode — for sensitive data)
// Server -> Client, inside InputRequiredResult.inputRequests:
{ "method": "elicitation/create", "params": {
    "mode": "url", "url": "https://mcp.example.com/ui/set_api_key",
    "message": "Please provide your API key to continue." } }
// Client -> Server, inside inputResponses on the retried request:
{ "action": "accept" }
```

**Form mode requestedSchema (restricted subset — flat objects, primitives only):** top-level `{ $schema?, type: "object", properties: { [key]: PrimitiveSchemaDefinition }, required? }`. `PrimitiveSchemaDefinition = StringSchema | NumberSchema | BooleanSchema | EnumSchema`. No nesting, no arrays-of-objects beyond enums. String formats: `email|uri|date|date-time`. Number: `type: "number"|"integer"` with `minimum`/`maximum`/`default`. Enum: single-select (`type:"string"` + `enum[]` or `oneOf[{const,title}]`) or multi-select (`type:"array"` + `items:{type:"string",enum[]}` or `items:{anyOf:[{const,title}]}`), with `minItems`/`maxItems`/`default`. All primitives support optional `default`.

**Security rule (critical):** servers MUST NOT use form mode to request **sensitive information** (passwords, API keys, access tokens, payment credentials) — those MUST use URL mode. "Sensitive" = secrets/credentials granting access or authorizing transactions; general contact/profile info (name, email, username) is not categorically prohibited.

**URL mode:** directs the user to an external URL for out-of-band interaction that must NOT pass through the MCP client (auth flows, payment, sensitive data). The client's only responsibility is to present the URL with context + consent; the client's bearer token is unchanged. `action:"accept"` means the user consented to the interaction, NOT that it completed — the interaction happens out of band; on retry the server determines from echoed `requestState`/stored state whether it finished, and either returns the final result or another `InputRequiredResult`.

**Response actions (three-action model):** `accept` (user approved+submitted; form mode carries `content` matching the schema, URL mode omits it), `decline` (explicit reject, content typically omitted), `cancel` (dismissed without explicit choice — closed dialog, Escape, browser failure; content omitted). Servers handle each: accept→process data, decline→offer alternatives, cancel→prompt again later.

**Statefulness:** elicitation doesn't require server-side state via MRTR. If state IS stored, it MUST be protected against unauthorized access, and for remote servers user identification MUST derive from MCP-authorization credentials (e.g. `sub` claim) when possible.

**Invariant:** form mode is in-band (data exposed to client) and must never carry secrets; URL mode is out-of-band (data never exposed to client) and is the only legal path for sensitive info. A porter who requests an API key via form mode, or who treats `accept` in URL mode as "done", breaks the security/UX contract.

**Probe:** no runtime tests in the spec repo; wire types (`ElicitRequestFormParams`/`ElicitRequestURLParams` discriminated by `mode`) + `scripts/validate-examples.ts` are the machine-checkable anchors. Coverage caveat recorded honestly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "modelcontextprotocol", name_pattern: "Elicitation.Form.Mode|Sensitive.Information|Response.Actions|ElicitRequestParams", limit: 10 });
```

## Verdict
Adopt the `elicitation/create` contract — flat-primitive `requestedSchema` subset, form-vs-URL mode split with sensitive-data-only-in-URL, and the accept/decline/cancel response model; adapt your form field schemas, URL set, and consent UX to host; omit nothing here (elicitation is NOT deprecated — it's the current mechanism for gathering user input).
