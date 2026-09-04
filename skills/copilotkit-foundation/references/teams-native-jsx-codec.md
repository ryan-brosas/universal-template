<!-- capsule-v2 -->
# teams-native-jsx-codec

## Source
- Repo: `copilotkit` (MIT)
- Path: `packages/channels-teams/src/native-codec.ts`
- Symbol: `renderTeamsNativeCard` / `containsTeamsNative` / `serializeTeamsNode`
- Lines: renderTeamsNativeCard :16-41, containsTeamsNative :44-46, serializeTeamsNode :48-132
- Commit: `e9387e04835545c45744b791aee7c9c03520be31`
- Graph Node: `ext-copilotkit.packages.channels-teams.src.native-codec.renderTeamsNativeCard`

## Question
When an agent emits provider-NATIVE JSX (an explicit `Teams.AdaptiveCard` root) instead of portable IR, how is it validated and serialized without letting cross-provider payloads or interactive raw objects slip through?

## Signature & Data Shape
```typescript
renderTeamsNativeCard(ir: ChannelNode[]): AdaptiveCard;  // throws on every structural violation
containsTeamsNative(ir: readonly ChannelNode[]): boolean; // adapter render-fork gate (checked BEFORE plain/card lowering)
```
Manifest lookup key: `` `${entry.kind}:${entry.component}` `` from `TEAMS_NATIVE_MANIFEST`; handler props are a closed set `new Set(["onClick","onSelect","onSubmit"])`.

## Decisive Source Excerpt
```typescript
if (ir.length !== 1 || !isNativeNode(ir[0]))
  throw new Error("Teams native JSX requires one explicit Teams.AdaptiveCard root.");
const root = ir[0];
if (root.props.provider !== "teams")
  throw new Error("Teams delivery cannot render Slack native JSX.");   // LOUD cross-provider refusal
...
if (typeof explicit === "string" && compareVersions(explicit, required) < 0) {
  const cause = highestVersionNode(root);
  throw new Error(`Teams.${cause.name} requires Adaptive Card ${cause.version}; root version ${explicit} is too low.`);
}
```
Raw passthrough guard inside `serializeTeamsNode`: `assertRawIsNonInteractive(node.props.value, `${path}.Raw`)` — a `nativeKind:"raw"` object must not carry interactivity that would bypass the registry.

## Flow
1. Adapter `render()` checks `containsTeamsNative(ir)` FIRST — native roots bypass the markdown/Adaptive-Card lowering entirely.
2. Structural validation ladders with path-tagged errors: exactly-one-root → provider match (`teams`) → `nativeKind === "root"` → explicit `version` must be ≥ the highest version REQUIRED by any node inside (`requiredVersion(root)` walks the manifest).
3. Serialization recurses per node: manifest entry supplies the wire `type` + fixedProps; `provider`/`nativeKind`/`nativeType`/`children`/`version`/handler props are transport metadata stripped from output; unknown manifest keys throw loudly rather than dropping.
4. Errors name the offending path (`${path}: …`, e.g. `Teams.AdaptiveCard.Raw`) so an author can find the bad node in a big tree.

## Invariant
A native payload is delivered byte-faithful or NOT AT ALL — validation failures throw before any network call, cross-provider native JSX never silently re-renders through the portable renderer, and declared card version is enforced against the minimum required by the tree's most demanding node.

## Direct-Test Probe
- File: `packages/channels-teams/src/native-jsx.test.tsx` (+ `native-catalog.test.ts`, `native-interaction.test.ts`)
- Pins: single-root requirement, Slack-native-on-Teams refusal, version-floor error message, Raw non-interactivity

## Graph Query
```bash
codebase-memory-mcp cli search_graph '{"project":"ext-copilotkit","query":"renderTeamsNativeCard nativeKind provider serializeTeamsNode","limit":10}'
```

## Verdict
Adopt the validate-loud-serialize-faithful codec shape and the version-floor computation. Adapt the manifest vocabulary per provider. Omit nothing — the cross-provider refusal and raw non-interactivity assert are the security-relevant halves.
