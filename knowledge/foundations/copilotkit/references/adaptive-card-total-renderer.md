<!-- capsule-v2 -->
# adaptive-card-total-renderer

## Source
- Repo: `copilotkit` (MIT)
- Path: `packages/channels-teams/src/render/adaptive-card.ts`
- Symbol: `renderAdaptiveCard` / `renderNode` / `fieldId` / `renderButton` / `isPlainText`
- Lines: renderAdaptiveCard :46-64, renderNode :67-156, fieldId :243-265, renderButton :184-211, isPlainText :440-462
- Commit: `e9387e04835545c45744b791aee7c9c03520be31`
- Graph Node: `ext-copilotkit.packages.channels-teams.src.render.adaptive-card.renderAdaptiveCard`

## Question
How do you lower a cross-platform component IR tree into a Teams Adaptive Card so that no input crashes the renderer, no card exceeds Teams' payload ceiling, and button clicks can still be routed back to the engine?

## Signature & Data Shape
```typescript
function renderAdaptiveCard(ir: ChannelNode[]): AdaptiveCard;   // total: never throws on unknown intrinsics
function fieldId(node, handlerProp: "onSelect"|"onSubmit", fallback: "select"|"input", ctx): string;
function isPlainText(ir: ChannelNode[]): boolean;               // RICH-set membership test over the whole tree
```
Reserved-id rule: `RenderContext.usedFieldIds` starts as `new Set(["ckActionId", "value"])`.

## Decisive Source Excerpt
```typescript
const action: CardAction = { type: "Action.Submit",
  title: truncateText(collectText(node), TEAMS_LIMITS.buttonText) };
// Forward-ready: carry the opaque action id + value so a later
// `decodeInteraction` can route the submit back into the engine.
const id = idFromHandler(props.onClick);            // reads `{ id }` stamped by the action registry
if (id) data.ckActionId = id;
if (props.value !== undefined) data.value = props.value;
...
case "input": body.push(renderInput(node, fieldId(node, "onSubmit", "input", context)));
```
And the collision-free id ladder (`fieldId`, :256-264):
```typescript
const base = explicitName ?? idFromHandler(props[handlerProp]) ?? `${fallback}_${index}`;
let candidate = base, suffix = 1;
while (context.usedFieldIds.has(candidate)) candidate = `${base}_${suffix++}`;
context.usedFieldIds.add(candidate);
```

## Flow
1. Structural nodes map to body elements (header→large bold TextBlock, Fields→FactSet with first-colon title/value split at idx ≤ 60, Table→native Table with inferred column count from the widest row when columns are absent, Chart→Teams host-extension chart elements that non-Teams hosts ignore).
2. Buttons become top-level actions: URL buttons → `Action.OpenUrl`; everything else → `Action.Submit` carrying `{ ckActionId, value }` in its data — the registry-stamped opaque id is what makes the later `parseCardAction(activity)` round-trip work.
3. Inputs/selects get ids from explicit name → handler-stamped id → indexed fallback, de-duplicated against the used-set which PRE-SEEDS `ckActionId`/`value` so form fields can never shadow Action.Submit routing data.
4. Every collection clamps and every string truncates via `TEAMS_LIMITS` (budget module twin of WhatsApp's); unknown intrinsics are skipped silently (total renderer).
5. `isPlainText` gates the adapter's render fork — text-only trees go out as plain text activities ("a bare Echo: hi shouldn't render as a card"); anything touching the RICH set becomes a card.

## Invariant
The renderer is total (no throw on any IR), budget-clamped at every leaf (card stays under Teams' ceiling), and interaction-routing data (`ckActionId`) plus submitted-field ids live in disjoint namespaces.

## Direct-Test Probe
- File: `packages/channels-teams/src/render/adaptive-card.test.ts`
- Lines: :69 Button as Action.Submit carrying opaque id; :117 Select/Input as body inputs; :150 stable names + collision-free fallbacks; :180 form fields cannot overwrite Action.Submit routing data; :213 clamps top-level actions; :221 skips unknown intrinsics without throwing

## Graph Query
```bash
codebase-memory-mcp cli search_graph '{"project":"ext-copilotkit","query":"renderAdaptiveCard Action.Submit ckActionId fieldId","limit":10}'
```

## Verdict
Adopt the total-renderer + reserved-routing-id + collision-ladder trio for any IR→native-card lowering. Adapt element vocabulary and limits to the target card schema. Omit nothing — pre-seeding the reserved set is the subtle half of the routing invariant.
