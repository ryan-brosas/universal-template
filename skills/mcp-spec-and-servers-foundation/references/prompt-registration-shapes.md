<!-- capsule-v2 -->
# Prompt registration shapes — what are the canonical `registerPrompt` forms (no-args, required+optional args, embedded resource, completer-backed), and where does validation happen?

**Source:** modelcontextprotocol/servers MIT `main@76d64c82`; Codebase Memory `servers`. **Question:** How do server authors declare prompt arguments and return message lists, and which argument-validation discipline do the reference prompts enforce?

## Four canonical forms over one handler contract
**Path/Symbol:** `src/everything/prompts/simple.ts` (whole file, 29L), `src/everything/prompts/args.ts` (whole file, 41L: optional-arg composition :24–27), `src/everything/prompts/resource.ts` (whole file, 93L: completer-backed schema :25–28; manual validation :38–61; two-message embed :73–90). Completer sources: `resources/templates.ts` exports `resourceTypeCompleter` (:27) and `resourceIdForPromptCompleter` (:50).

**Signature:** `server.registerPrompt(name, { title?, description?, argsSchema? }, (args) => ({ messages: [{ role, content }] }))`. `argsSchema` is a plain zod-shape object (NOT wrapped in z.object); each property's `.describe()` feeds the client-facing argument metadata; `.optional()` marks non-required args.

**Data Shape:** handlers return `{ messages }`; user-role text messages carry instructions; resource embedding uses a SECOND message whose content block is `{ type: "resource", resource }`.

### Decisive source
```ts
// prompts/args.ts:20-33 — optional arg composed into the template, never assumed present
(args) => {
  const location = `${args?.city}${args?.state ? `, ${args?.state}` : ""}`;
  return { messages: [{ role: "user",
    content: { type: "text", text: `What's weather in ${location}?` } }] };
}
```
```ts
// prompts/resource.ts:40-56 — re-validate enum + integer even though completers constrain input
const resourceType = args.resourceType;
if (!RESOURCE_TYPES.includes(resourceType)) { throw new Error(`Invalid resourceType: ...`); }
const resourceId = Number(args?.resourceId);
if (!Number.isFinite(resourceId) || !Number.isInteger(resourceId) || resourceId < 1) { throw new Error(`Invalid resourceId: ...`); }
```

**Flow:** static prompt = zero-arg closure returning fixed text → argumented prompt = destructure with `?.`, compose optional parts conditionally → resource prompt = validate type/id manually → build URIs via shared template builders → return instruction message PLUS a separate resource-content message → completer-backed schemas additionally serve `completion/complete` for the same args (see `resource-template-completers.md`, `dependent-argument-completion.md`).

**Invariants:**
1. **Optional args are composed defensively** (`args?.state ? … : ""`) — a porter who interpolates without guards renders "undefined" into prompts.
2. **Completers narrow UX but don't replace validation**: clients may bypass completion; the handler re-checks enum membership and positive-integer id before constructing URIs.
3. **Embedded resources ride their own message**, not an inline text mention — clients render typed resource content distinctly.
4. Prompt handlers THROW on invalid args (error surfaces as the protocol error of prompts/get) rather than rendering fallback text.

**Probe:** `src/everything/__tests__/prompts.test.ts` pins all four registrations (message shape, arg handling, embedded-resource round-trip). Coverage caveat: suite asserts happy paths; the invalid-arg throw paths are pinned only by source (:46–60).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "servers", query: "registerPrompt argsSchema completable prompt messages embedded resource", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt the four registration forms with defensive optional-arg composition, completer-plus-revalidation discipline, and per-message resource embedding; adapt prompt catalogs to your product; omit demo copy. Complements the two completion capsules, which own the autocomplete surface these schemas advertise.
