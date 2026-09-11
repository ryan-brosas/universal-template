<!-- capsule-v2 -->
# Cursor protobuf model discovery — how do you recover capability truth a binary RPC doesn't send?

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** When `GetUsableModels` returns neither context windows nor reasoning flags, how do you reconstruct them?

## Signal-laddered inference over a hand-rolled zero-builder protobuf codec
**Path/Symbol:** `packages/catalog/src/discovery/cursor.ts` (constants :9–41, inference patterns), `discovery/protobuf.ts` (`MessageCodec`, lazy compile), `discovery/cursor-proto.ts` (@generated IR).
**Signature:** `fetchCursorUsableModels({apiKey, baseUrl?, clientVersion?}): Promise<ModelSpec[]>` over http2 POST `/agent.v1.AgentService/GetUsableModels`.
**Data Shape:** generated codecs retain ONLY consumed fields plus `$unknown` forward-compat bags; schemas are static IR with lazy first-use compilation.

### Decisive source
```ts
// GetUsableModels carries NO context-window field — the 1M ceiling is
// recovered from the signals Cursor does send:
const CURSOR_1M_NAME_PATTERN = /\b1m\b/i;                    // display labels
const CURSOR_MAX_MODE_1M_ID_PATTERN = /claude|gemini/;       // max-mode ids
// Kimi K3 + GLM 5.2+ are natively 1M families served unlabeled.
const CURSOR_KIMI_K3_BARE_ID_PATTERN = /(^|\/)k3$/i;         // k3-256k stays out

// Versioned Grok ids reason via per-tier sibling ids and GetUsableModels
// ships no thinkingDetails, so classification falls back to the id.
const CURSOR_GROK_REASONING_ID_PATTERN = /^cursor-grok-\d/i;
```

**Flow:** http2 session to api2.cursor.sh with pinned client version → binary request via generated codec → decode tolerant of unknown fields → per-model: displayName/aliases parsed defensively (type-schema pipes) → context window from label/max-mode/native-family ladder → reasoning/multimodal from id-family patterns → bundled references merged for limits/pricing.
**Invariant:** (1) every absent field gets an explicit inference ladder documented in-source rather than a silent default; (2) `k3-256k` must NOT match the bare-K3 1M pattern (boundary-guarded regex); (3) generated files are never hand-edited — regeneration flows through scripts/proto-parser.ts.
**Probe:** direct `packages/catalog/test/cursor-discovery.test.ts` (whole-pipeline fixtures) + `test/variant-collapse.test.ts:677/:737/:788` (tier routing on discovered ids #8803/#9025/#9237).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "fetchCursorUsableModels GetUsableModels cursor proto", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt the signal-ladder pattern when an upstream discovery API under-reports capabilities; adapt ladders to what your target actually sends; omit the protobuf toolchain unless you speak this RPC. Coverage caveat: none for discovery pipeline; codec internals tested via protobuf.test.ts.
