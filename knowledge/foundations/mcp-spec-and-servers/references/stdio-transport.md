<!-- capsule-v2 -->
# stdio transport — what does newline-delimited JSON-RPC over a subprocess require, and how do you shut down and fall back cleanly?

**Source:** modelcontextprotocol/specification MIT `main@4df2d6b`; Codebase Memory `modelcontextprotocol`. **Question:** Which stream-purity, cancellation, shutdown, and era-probe rules must a stdio server/client obey?

## One channel, absolute stdout purity
**Path/Symbol:** `docs/specification/draft/basic/transports/stdio.mdx` (channel rules :7–31; message kinds :39–63; inline metadata :65–74; cancellation :76–85; shutdown :87–107; unexpected termination :109–115; backward compatibility :121–150).

### Decisive source
```md
# stdio.mdx:10-21 (the framing contract)
- The server reads JSON-RPC messages from stdin and writes JSON-RPC messages to stdout.
- Messages are delimited by newlines, and MUST NOT contain embedded newlines.
- The server MAY write UTF-8 strings to stderr for any logging purposes...
- The server MUST NOT write anything to its stdout that is not a valid MCP message.
- The client MUST NOT write anything to the server's stdin that is not a valid MCP message.
```
The wire format generalizes: one newline-delimited JSON-RPC message per line over any reliable bidirectional byte stream (Unix socket, TCP) reuses these rules — only subprocess-specific parts (launch, stderr, close-to-shutdown, restart) need channel equivalents (:23–31). All metadata rides in the body `_meta` (`io.modelcontextprotocol/*` keys); there is NO header layer on stdio (:65–74).

**Three outbound kinds** (:44–58): responses correlated by id; notifications related to an in-flight request (`notifications/progress`, `notifications/message`); notifications for active `subscriptions/listen` requests — clients MUST demux those via `io.modelcontextprotocol/subscriptionId`. The server **MUST NOT** write JSON-RPC requests to stdout; server-needs-input goes through MRTR `InputRequiredResult`.

**Cancellation & shutdown** (:76–107): cancel = send `notifications/cancelled` referencing the request id (single shared channel — there is no stream to close; the same notification from a SERVER only ever terminates a `subscriptions/listen` stream). Client shutdown ladder: close child's stdin → wait → SIGTERM→SIGKILL escalation (POSIX) / TerminateProcess or Job Objects (Windows). Server SHOULD exit promptly on stdin EOF — "the primary graceful-shutdown signal and the only portable one." Unexpected exit ⇒ client restarts; protocol is stateless so in-flight requests are simply lost and subscriptions must be re-established (:109–115).

**Era probe** (:123–147): client supporting both eras SHOULD send `server/discover` first. `DiscoverResult` ⇒ modern; recognized modern error (`UnsupportedProtocolVersionError`) ⇒ modern but wrong version — use its advertised list, do NOT fall back; any other error OR timeout ⇒ legacy ⇒ `initialize`. The fallback MUST NOT key off one specific error code — legacy servers answer unknown methods with implementation-defined errors (`-32601`, `-32602`) or silence. Modern-only clients are still RECOMMENDED to probe: some legacy servers would process `tools/call` under legacy semantics without it.

**Invariant:** stdout carries ONLY complete single-line MCP messages — a porter who `console.log`s diagnostics to stdout corrupts the framing and wedges every client parser; all logging goes to stderr. And because one channel carries everything, subscription notifications without `subscriptionId` are unassignable.

**Probe:** no runtime tests in the spec repo (docs+schema); machine-checkable anchors are `CancelledNotification` (schema.ts :648–651 — documents the server-side listen-stream-only exception), `DiscoverRequest/Result` (:665–709). Coverage caveat recorded honestly.

## Get live surrounding code
**Retrieve:** (`query` BM25 now zero-hits this doc-shaped graph — noise-label filtering; use `name_pattern`):
```bash
codebase-memory-mcp cli search_graph --project modelcontextprotocol \
  --name-pattern 'StdioServerTransport|cancelled|discover' --limit 10
```

## Verdict
Adopt newline-delimited framing with stdout purity, stderr logging, stdin-EOF-first shutdown with signal escalation, notification-based cancellation, and the discover-probe era fallback that never trusts a single error code; adapt process supervision/restart policy to your host runner; omit custom-transport extensions unless you are binding a new channel.
