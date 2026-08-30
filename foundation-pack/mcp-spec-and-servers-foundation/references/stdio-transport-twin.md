<!-- capsule-v2 -->
# stdio transport twin — what does the minimal reference main() look like, and which exit-path details matter?

**Source:** modelcontextprotocol/servers MIT `main@76d64c822f5125032f89eb71dbdb94e42b434821` (src/everything); Codebase Memory `servers`. **Question:** How does a production stdio MCP server bootstrap, and what must SIGINT cleanup preserve?

## connect → SIGINT → close → cleanup → exit 0
**Path/Symbol:** `src/everything/transports/stdio.ts` (whole file, 33L: `main()` :15–28; catch-all :30–33). Pairs with the factory (`server-factory` capsule): `createServer()` returns `{ server, cleanup }`.

**Signature:** `async function main(): Promise<void>` — construct `StdioServerTransport`, destructure `{ server, cleanup }` from the factory, `await server.connect(transport)`, register ONE `process.on("SIGINT")` handler.

### Decisive source
```ts
// src/everything/transports/stdio.ts:15-33 (complete)
async function main(): Promise<void> {
  const transport = new StdioServerTransport();
  const { server, cleanup } = createServer();

  // Connect transport to server
  await server.connect(transport);

  // Cleanup on exit
  process.on("SIGINT", async () => {
    await server.close();     // protocol-level teardown FIRST (awaited)
    cleanup();                // factory-registered resource disposal SECOND
    process.exit(0);
  });
}

main().catch((error) => {
  console.error("Server error:", error);
  process.exit(1);
});
```

**Flow:** startup = transport → factory → connect (three statements); shutdown ladder on SIGINT = `await server.close()` (drains in-flight handlers / closes transport) THEN `cleanup()` (factory closure disposing session resources — see `server-factory`) THEN `process.exit(0)` with explicit success code. Any async error anywhere lands in the `.catch` ⇒ `console.error` to STDERR (never stdout — stdout is the protocol channel per `stdio-transport`) + `process.exit(1)`.

**Invariant:** ordering — protocol close BEFORE resource cleanup BEFORE exit; a porter who runs `cleanup()` first can have `server.close()` flush notifications into already-disposed resources. Diagnostics go to stderr only. Exit codes are deliberate: 0 on signal-shutdown, 1 on fatal. Note this twin registers ONLY SIGINT: SIGTERM handling is left to the host (coverage caveat if you need it).

**Probe:** no dedicated vitest file instantiates `transports/stdio.ts` (the everything suite tests factory/tools/prompts/resources instead — coverage caveat recorded honestly); the observable boundary is the documented stdio contract in spec-side `stdio-transport.md` capsule (stdout purity, newline framing).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "servers", query: "main stdio transports server", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt the three-step bootstrap and the close→cleanup→exit-0 SIGINT ladder with stderr-only diagnostics for any Node stdio MCP server; adapt signal set (add SIGTERM if your host requires it) and logging destinations; omit extra session machinery — stdio is inherently single-session.
