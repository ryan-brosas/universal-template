<!-- capsule-v2 -->
# acp-tool-adapter-protocol

## Source
- Repo: `mastra`
- Path: `agent-sdks/acp/src/tool.ts`
- Symbol: `createACPTool`
- Lines: 8-56
- Commit: `3d2ff0d0a959792331f7cfb12dab6d08506676e7`
- Graph Node: `ext-mastra.agent-sdks.acp.src.tool.createACPTool`

## Signature & Data Shape
```typescript
export function createACPTool(options: CreateACPToolOptions): Tool<
  { task: string },
  { output: string },
  { permissionRequest: { title: string; options: Array<{ optionId: string; name: string }> } },
  { optionId?: string; outcome?: 'selected' | 'cancelled' }
>;
```

## Decisive Source Excerpt
```typescript
export function createACPTool(options: CreateACPToolOptions) {
  const session = new ACPToolSession(options);

  return createTool({
    id: options.id,
    description: options.description,
    inputSchema: compileSchema(
      z.object({
        task: z.string().describe('The task to send to the ACP agent'),
      }),
    ),
    outputSchema: compileSchema(
      z.object({
        output: z.string().describe('The output of the ACP agent'),
      }),
    ),
    suspendSchema: compileSchema(
      z.object({
        permissionRequest: z.object({
          title: z.string().describe('The title of the permission request'),
          options: z.array(
            z.object({
              optionId: z.string().describe('The option id to select'),
              name: z.string().describe('The title of the permission request'),
            }),
          ),
        }),
      }),
    ),
    resumeSchema: compileSchema(
      z.union([
        z.object({
          optionId: z.string().optional().describe('The option id to select'),
          outcome: z.literal('selected').optional().describe('The outcome of the permission request'),
        }),
        z.object({
          outcome: z.literal('cancelled').optional().describe('The outcome of the permission request'),
        }),
      ]),
    ),
    execute: async ({ task }, context) => {
      const workspace = await context?.mastra?.getWorkspace();
      const connection = session.getConnection(workspace);
      const output = await connection.prompt(task, context?.abortSignal);

      return { output };
    },
  });
}
```

## Flow
1. Instantiate `ACPToolSession` carrying connection lifecycle parameters.
2. Compile formal input and output schemas (`task` input $\to$ `output` string).
3. Bind typed `suspendSchema` representing an interactive ACP permission request (`permissionRequest` with title and selectable option list).
4. Bind dual-outcome `resumeSchema` handling both `'selected'` with chosen `optionId` and `'cancelled'`.
5. On `execute`, resolve workspace context, get active connection, and dispatch prompt forwarding the execution abort signal.

## Invariant
Interactive ACP permission prompts must define explicit, bidirectional suspend/resume schema contracts (`selected` vs `cancelled` union) rather than opaque strings, guaranteeing typed HITL resolution across remote ACP agents.

## Direct-Test Probe
- File: `agent-sdks/acp/src/__tests__/tool.test.ts`
- Lines: 15-50
- Suite: `describe('createACPTool')`

## Graph Query
```bash
codebase-memory-mcp cli search_graph '{"project":"ext-mastra","query":"createACPTool ACPToolSession permissionRequest"}'
```

## Verdict
Adopt the typed ACP tool adapter contract and permission suspend/resume schema union.
