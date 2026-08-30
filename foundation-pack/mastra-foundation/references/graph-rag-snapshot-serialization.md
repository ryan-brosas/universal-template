<!-- capsule-v2 -->
# graph-rag-snapshot-serialization

## Source
- Repo: `mastra`
- Path: `packages/rag/src/graph-rag/index.ts`
- Symbol: `GraphRAG.serialize` / `GraphRAG.deserialize`
- Lines: 115-166
- Commit: `3d2ff0d0a959792331f7cfb12dab6d08506676e7`
- Graph Node: `ext-mastra.packages.rag.src.graph-rag.GraphRAG.serialize`

## Signature & Data Shape
```typescript
export interface GraphNode {
  id: string;
  content: string;
  embedding?: number[];
  metadata?: Record<string, any>;
}

export interface GraphEdge {
  source: string;
  target: string;
  weight: number;
  type: 'semantic';
}

export interface GraphRAGSnapshot {
  version: 1;
  dimension: number;
  threshold: number;
  nodes: GraphNode[];
  edges: GraphEdge[];
}
```

## Decisive Source Excerpt
```typescript
serialize(): GraphRAGSnapshot {
  return {
    version: GRAPH_RAG_SNAPSHOT_VERSION,
    dimension: this.dimension,
    threshold: this.threshold,
    nodes: Array.from(this.nodes.values()).map(node => ({
      ...node,
      ...(node.embedding ? { embedding: [...node.embedding] } : {}),
      ...(node.metadata ? { metadata: structuredClone(node.metadata) } : {}),
    })),
    edges: this.edges.map(edge => ({ ...edge })),
  };
}

static deserialize(snapshot: GraphRAGSnapshot): GraphRAG {
  if (snapshot?.version !== GRAPH_RAG_SNAPSHOT_VERSION) {
    throw new Error(`Unsupported GraphRAG snapshot version: ${snapshot?.version}`);
  }

  const graph = new GraphRAG(snapshot.dimension, snapshot.threshold);

  for (const node of snapshot.nodes ?? []) {
    // Route through addNode so embedding presence and dimension are validated
    // at load time rather than failing later inside query().
    graph.addNode({
      ...node,
      ...(node.embedding ? { embedding: [...node.embedding] } : {}),
      ...(node.metadata ? { metadata: structuredClone(node.metadata) } : {}),
    });
  }

  for (const edge of snapshot.edges ?? []) {
    if (!graph.nodes.has(edge.source)) {
      throw new Error(`Edge references unknown node: ${edge.source}`);
    }
    if (!graph.nodes.has(edge.target)) {
      throw new Error(`Edge references unknown node: ${edge.target}`);
    }
  }

  // Assign directly rather than via addEdge: the serialized edge list already
  // contains both directions, and addEdge would add the reverse edge again.
  graph.edges = (snapshot.edges ?? []).map(edge => ({ ...edge }));

  return graph;
}
```

## Flow
1. `serialize`: Deep-clone all node metadata via `structuredClone` and copy embedding arrays.
2. `deserialize`: Verify `snapshot.version === 1`.
3. Reconstruct graph: iterate nodes through `addNode` to validate embedding length against `dimension`.
4. Validate that all edges reference existing node IDs.
5. Direct-assign edge list without calling `addEdge`, preventing duplicate reciprocal edges.

## Invariant
Deserialization must never call `addEdge` because serialized snapshots already contain reciprocal edges; calling `addEdge` during rehydration would double edge counts. Node embeddings must be verified at load time rather than query time.

## Direct-Test Probe
- File: `packages/rag/src/graph-rag/index.test.ts`
- Lines: 40-95
- Suite: `describe('GraphRAG serialization')`

## Graph Query
```bash
codebase-memory-mcp cli search_graph '{"project":"ext-mastra","query":"GraphRAG serialize deserialize GRAPH_RAG_SNAPSHOT_VERSION"}'
```

## Verdict
Adopt the JSON snapshot schema and direct-assignment deserialization pattern for in-memory graph engines.
