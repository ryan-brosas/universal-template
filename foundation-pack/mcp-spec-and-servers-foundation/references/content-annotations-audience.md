<!-- capsule-v2 -->
# Content-block annotations — how do audience/priority annotations steer client display of text/image blocks?

**Source:** modelcontextprotocol/servers MIT `main@76d64c822f5125032f89eb71dbdb94e42b434821` (src/everything); Codebase Memory `servers`; wire types modelcontextprotocol/specification MIT `main@4df2d6b6e3588efb46e7542d98498e5c630a0a86`. **Question:** What is the exact `Annotations` shape on content blocks, and how does the reference server assign audience/priority per message type?

## Role[] + 0..1 priority per block; reference values as calibration table
**Path/Symbol:** servers `src/everything/tools/get-annotated-message.ts` (whole file: schema :7–15; tool annotations :24–29; branch ladder :51–78; annotated image :81–91). Wire type spec repo `schema/draft/schema.ts` `Annotations` :2270–2289 — `audience?: Role[]` (`"user" | "assistant"`), `priority?: number` (@minimum 0 @maximum 1); attached to TextResourceContents-side resources :1464, resource templates :1504, embedded resources :1741, and every content block incl. text :2327.

**Signature:** `annotations?: { audience?: ("user"|"assistant")[]; priority?: number /* 0=entirely optional .. 1=effectively required */ }` — schema doc (:2272–2274): "It can include multiple entries to indicate content useful for multiple audiences (e.g., `[\"user\", \"assistant\"]`)"; (:2278–2283): "A value of 1 means 'most important,' and indicates that the data is effectively required, while 0 means 'least important'".

### Decisive source
```ts
// src/everything/tools/get-annotated-message.ts:51-77 — the reference calibration
if (messageType === "error") {
  content.push({ type: "text", text: "Error: Operation failed",
    annotations: { priority: 1.0,                  // Errors are highest priority
                   audience: ["user", "assistant"] } }); // Both need to know about errors
} else if (messageType === "success") {
  content.push({ type: "text", text: "Operation completed successfully",
    annotations: { priority: 0.7,                  // important but not critical
                   audience: ["user"] } });        // Success mainly for user consumption
} else if (messageType === "debug") {
  content.push({ type: "text", text: "Debug: Cache hit ratio 0.95, latency 150ms",
    annotations: { priority: 0.3,                  // Debug info is low priority
                   audience: ["assistant"] } });   // Technical details for assistant
}
// :81-91 optional image → { priority: 0.5, audience: ["user"] }
```

**Flow:** tool builds a multi-block result → each block carries its own annotations object → client filters rendering by `audience` (hide assistant-only debug from the user UI; hide user-only imagery from the model context) and ranks/truncates by `priority` when context is tight. The same Annotations type also decorates RESOURCES and embedded-resource blocks, not just chat text.

**Invariant:** these annotations are CLIENT DISPLAY HINTS about individual data blocks — distinct from ToolAnnotations (behavior hints about the whole tool, see `tool-annotations-hints`) and carrying no authorization weight. Priority bounds [0,1] are schema-enforced; audience is a closed two-value set. A porter who stuffs a third role or uses priority for access control breaks the contract.

**Probe:** `src/everything/__tests__/` covers the tool's registration family but pins no annotation VALUES (coverage caveat recorded honestly); the machine-checkable boundary is `Annotations` in `schema/draft/schema.ts`:2270–2289 plus the reference calibration above.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "modelcontextprotocol", name_pattern: "Annotations", limit: 10 });
```

## Verdict
Adopt per-block audience filtering with the error=1.0/user+assistant, success=0.7/user, debug=0.3/assistant, image=0.5/user calibration as defaults; adapt thresholds to your product's UX; omit using annotations for security decisions or extending the role set.
