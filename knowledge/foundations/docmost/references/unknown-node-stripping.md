<!-- capsule-v2 -->
# Unknown-node stripping — how do you render documents written by NEWER editor schemas without crashing?

**Source:** docmost AGPL-3.0 `main@549cf7c0053bb4f4c3c4e08d588b1f0c69297daf`; Codebase Memory `ext-docmost`. **Question:** How can a server with an older tiptap schema convert arbitrary stored JSON to a PM Node when it contains node types the schema doesn't know?

## jsonToNode RangeError fallback + unwrap-not-drop recursion
**Path/Symbol:** `apps/server/src/collaboration/collaboration.util.ts`:`jsonToNode` / `stripUnknownNodes` (lines 153–215); extension list `tiptapExtensions` (lines 69–132) and `htmlToJson`'s `addUniqueIdsToDoc` best-effort wrapper (lines 138–147).
**Signature:** `jsonToNode(tiptapJson: JSONContent): Node`; `stripUnknownNodes(json: JSONContent, schema: Schema): JSONContent | null`.
**Data Shape:** Returns a PM `Node`, or null for fully-unknown content; children of unwrapped unknown nodes are FLATTENED into the parent, never silently discarded.

### Decisive source
```ts
try {
  return Node.fromJSON(schema, tiptapJson);
} catch (error) {
  if (error instanceof RangeError && error.message.includes('Unknown node type')) {
    const cleanedJson = stripUnknownNodes(tiptapJson, schema);
    return Node.fromJSON(schema, cleanedJson);
  }
  throw error;
}
// inside stripUnknownNodes — clean children FIRST, then decide about self:
if (json.type && !schema.nodes[json.type]) {
  return (json.content && json.content.length > 0 ? json.content : null) as any;  // unwrap
}
```

**Flow:** attempt strict parse → on exactly "Unknown node type" RangeError, recurse: clean children, then replace any unknown node with its cleaned children array (array return = flatten into parent).
**Invariant:** only the Unknown-node RangeError triggers stripping — every other error propagates (a corrupt doc should fail loudly, not silently shrink). Cleaning runs depth-first children-before-self so an unknown CONTAINER's known grandchildren survive by being hoisted. The whole mechanism exists because collab servers must render docs produced by newer clients.
**Probe:** `grep -cF 'Unknown node type' apps/server/src/collaboration/collaboration.util.ts` (=1) and `grep -cF 'addUniqueIdsToDoc(pmJson, tiptapExtensions)' apps/server/src/collaboration/collaboration.util.ts` (=1).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-docmost", query: "stripUnknownNodes jsonToNode RangeError fromJSON", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt try/strict-parse + targeted-RangeError unwrap recursion as the forward-compat rendering guard; adapt to your schema object; omit the tiptap extension list itself (host-specific). No upstream direct test; pinned by source read + probes.
