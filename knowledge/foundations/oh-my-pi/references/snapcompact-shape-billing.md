<!-- capsule-v2 -->
# Snapcompact shape selection — provider-aware frame geometry and per-frame billing

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** How does a porter pick the right bitmap-frame shape (font, cell pitch, frame size) and per-frame token bill for a given model/provider, without re-running the SQuAD/toolbench evals?

## Shape resolution
**Path/Symbol:** `packages/snapcompact/src/snapcompact.ts:resolveShape` (399–407), `resolveShapeForText` (432–442), `idealShapeVariant` (366–382), `billingFamily` (208–226), `familyBilling` (238–251), `SHAPES` (259–277), `MODEL_VARIANTS` (346–363).
**Signature:** `resolveShape(model?: ShapeTarget, variant?: ShapeVariantName | "auto"): Shape`; `resolveShapeForText(text, model?, variant?): Shape`.
**Data Shape:** `Shape = { font, cellWidth, cellHeight, stretch?, variant: "sent"|"bw", stopwordDim?, columns?, lineRepeat, frameSize, frameTokenEstimate, imageDetail? }`. `ShapeTarget = { api?: Api, id?: string }`. Eval-winning defaults per family: anthropic `11on16-bw`, google/openai/unknown `8on22-bw`.

### Decisive source
```ts
function billingFamily(api?: Api): BillingFamily {
  switch (api) {
    case "anthropic-messages": case "bedrock-converse-stream": return "anthropic";
    case "openai-completions": case "openai-responses": case "openai-codex-responses":
    case "azure-openai-responses": return "openai";
    case "google-generative-ai": case "google-gemini-cli": case "google-vertex": return "google";
    default: return "unknown";   // Anthropic pixel-area pricing as the safe ceiling
  }
}
function familyBilling(family, frameSize) {
  switch (family) {
    case "google": return { frameTokenEstimate: 1120 };   // fixed media_resolution budget
    case "openai": { const patches = Math.min(Math.ceil(frameSize/32)**2, 10_000);
                     return { frameTokenEstimate: Math.ceil(patches*1.2), imageDetail: "original" }; }
    default: { const patches = Math.min(Math.ceil(frameSize/28)**2, 4784);
               return { frameTokenEstimate: Math.ceil(patches*1.05) }; }
  }
}
```
`resolveShape`: explicit non-`"auto"` variant forces that geometry (re-priced for the actual API family); otherwise `idealShapeVariant(model.id)` picks the eval-winning shape by model line (`claude.*fable|mythos` and `opus≥4.7` → high-res 1932px `11on16-bw`; `claude` → 1568 `11on16-bw`; `gemini` → 2048 `8on22-bw`; `gpt|codex`/`kimi` → `8on22-bw`; `glm` → `8on16-bw`), falling back to the API family's winner. Billing always follows the API family actually carrying the request, computed for the resolved frame size. `resolveShapeForText` additionally switches to the `silver16-bw` CJK grid when the default font cannot safely render the text (via `scanRenderability`) or wide CJK glyphs dominate.

**Flow:** family ← api → explicit variant? price it : (ideal by model id → name/frameSize → price for family). Text-aware path re-checks renderability + CJK-heaviness and falls back to Silver.

**Invariant:** billing family is a function of the **API**, not the model id (a Claude via Vertex still bills as google); geometry is a function of the **model id**; frame size is chosen so it is not downscaled under the provider's visual-token cap (1932px = 69² = 4,761 ≤ 4,784 for high-res Claude; 2048 for Gemini's fixed budget).

**Probe:** `packages/snapcompact/test/snapcompact.test.ts:264` ("shape resolution" — asserts per-family `frameTokenEstimate` and the high-res Anthropic 1932px override); `:951` ("keeps foveated Silver archives on the Silver font" — CJK text resolves to `silver16-bw` and every frame keeps `font === "silver"`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "resolveShape billingFamily familyBilling SHAPES", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the API-family-vs-model-id split (billing by api, geometry by id) and the eval-winning shape table as the default — a porter who bills by model id or picks one global shape for all providers will misprice and mis-render. Adapt the eval numbers (they are opus/gemini/gpt-specific; re-bench for a different reader line). Omit the native font rasterizer. Coverage: `no_recorded_issue` + `metadata_match` on the `oh-my-pi` full index.
