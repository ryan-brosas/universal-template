<!-- capsule-v2 -->
# channel-ui-intermediate-representation

## Source
- Repo: `copilotkit`
- Path: `packages/channels-ui/src/render.ts`
- Symbol: `renderToIR` / `expand`
- Lines: 9-83
- Commit: `e9387e04835545c45744b791aee7c9c03520be31`
- Graph Node: `ext-copilotkit.packages.channels-ui.src.render.renderToIR`

## Signature & Data Shape
```typescript
export interface ChannelNode {
  type: string | ComponentFn | symbol;
  props: Record<string, unknown>;
  key?: string | number;
}

export type Renderable =
  | string
  | ChannelNode
  | ChannelNode[]
  | { raw: unknown; provider?: "slack" | "teams" };

export function renderToIR(ui: Renderable): ChannelNode[];
```

## Decisive Source Excerpt
```typescript
function expand(node: unknown): ChannelNode[] {
  if (node == null || node === false || node === true) return [];
  if (typeof node === "string" || typeof node === "number") {
    return [{ type: "text", props: { value: String(node) } }];
  }
  if (Array.isArray(node)) return node.flatMap(expand);
  if (!isChannelNode(node)) return [];
  if (node.type === Fragment) return expand(node.props.children);
  if (typeof node.type === "function") {
    const expanded = expand(
      (node.type as (p: Record<string, unknown>) => unknown)(node.props),
    );
    if (node.key !== undefined && expanded.length === 1 && expanded[0]) {
      expanded[0] = { ...expanded[0], key: expanded[0].key ?? node.key };
    }
    return expanded;
  }
  if (isNativeNode(node)) {
    return [
      {
        ...node,
        props: Object.fromEntries(
          Object.entries(node.props).map(([name, value]) => [
            name,
            expandNativeValue(value),
          ]),
        ),
      },
    ];
  }
  const { children, ...rest } = node.props;
  const expandedChildren =
    children === undefined ? undefined : expand(children);
  return [
    {
      type: node.type,
      props:
        expandedChildren === undefined
          ? rest
          : { ...rest, children: expandedChildren },
      key: node.key,
    },
  ];
}

export function renderToIR(ui: Renderable): ChannelNode[] {
  if (typeof ui === "object" && ui !== null && "raw" in ui) {
    const native = ui as {
      raw: unknown;
      provider?: "slack" | "teams";
    };
    return [
      {
        type: "raw",
        props: { value: native.raw, provider: native.provider ?? "slack" },
      },
    ];
  }
  return expand(ui);
}
```

## Flow
1. Check for `{ raw, provider }` escape hatches and project directly into raw IR nodes.
2. Flatten arrays and filter null/boolean elements.
3. Unwrap `Fragment` symbols by expanding children.
4. Execute component functions `node.type(node.props)` and propagate key assignments down to root child nodes.
5. Traverse native slots to expand embedded JSX nodes while preserving platform-specific layout structures.

## Invariant
UI intermediate representation expansion must recursively flatten fragments and component functions while propagating element keys and preserving platform raw payloads, establishing a single canonical IR tree across heterogeneous chat platforms.

## Direct-Test Probe
- File: `packages/channels-ui/src/render.test.tsx`
- Lines: 20-75
- Suite: `describe("renderToIR")`

## Graph Query
```bash
codebase-memory-mcp cli search_graph '{"project":"ext-copilotkit","query":"renderToIR expandNativeValue isChannelNode"}'
```

## Verdict
Adopt the Channel UI intermediate representation and recursive AST expander.
