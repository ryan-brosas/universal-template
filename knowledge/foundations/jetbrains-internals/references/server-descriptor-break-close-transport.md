<!-- capsule-v2 -->
# Server descriptor break/close transport grammar — how does a control plane address helper agents across transports without leaking transport details?

**Source:** JetBrains dotMemory standalone distribution (proprietary distribution; study/reference use only, citations-only), pin `?@?` (not git-managed; identity = install self-hash `41e6f647…` + Codebase Memory generation 2026-08-24T13:53:49Z); Codebase Memory `jetbrains-dotmemory` (5,124 nodes / 5,117 edges, FULL). **Question:** What minimal interface vocabulary lets one host talk to profiling/agent processes over tcp, named pipes, or anonymous pipes — and how should teardown semantics be split?

## Opaque (Type, Id) descriptor + two-verb teardown
**Path/Symbol:** `JetBrains.Profiler.Windows.SysTools.xml` (270L): `Impl.IConnection.{Break, Close}` (:49-63), `Impl.IServerDescriptor.{Type, Id, HumanReadable}` (:64-84), `Impl.IStreamServer` (:85-89), `Impl.TaskEx.RunAwait` (:90-95).
**Signature:** `void Break()`; `void Close()`; `IServerDescriptor.Type` / `.Id` / `.HumanReadable`; `TaskEx.RunAwait(Func<Task>)`.
**Data Shape:** a running server is published as ONE opaque descriptor whose `Id` meaning is selected by `Type` — port number for tcp, pipe name for named pipe, handle value for anon pipe.

### Decisive source
```text
IConnection.Break: "Rude and fast close a connection, no graceful shutdown"
IConnection.Close: "Graceful shutdown"
IServerDescriptor: "Opaque descriptor for running server. Fields can be used to
  connect to it abiding descriptor protocol"
IServerDescriptor.Type: "Type of server: tcp, named pipe, anon pipe, etc"
IServerDescriptor.Id:  "Identifier of server: port for tcp, name for named pipe,
  handle for anon pipe"
IStreamServer: "Represents server which can accept connections from clients and
  send/receive data to stream"
TaskEx.RunAwait: "Use for a adaptation synchronous and asynchronous logic to
  prevent deadlocks"
```

**Flow:** an agent/host side starts listening on whatever transport the platform offers → it hands out only the descriptor (never a socket, never a transport object) → any client that understands the descriptor protocol reconstructs the connection from `(Type, Id)` → during teardown the caller CHOOSES the verb: `Break` kills immediately when results no longer matter or the peer is wedged; `Close` drains gracefully when session state must survive.
**Invariant:** transport identity is the (Type, Id) PAIR — the Id string is meaningless without its Type discriminator, so descriptors must travel together with their type tag; rude vs graceful shutdown are two distinct API verbs, not flags, because callers need statically different intents; sync-context async execution needs an explicit adaptation helper documented as deadlock prevention.
**Probe:** deterministic content probes executed this pass on `$REFERENCE_ROOT/dotmemory/JetBrains.Profiler.Windows.SysTools.xml`: `grep -c "Rude and fast close"` = **1**, `grep -c "No that variable == no log"` = **2** (adjacency sanity for same file generation); decisive ranges :54-63/:69-78 verified by full 270-line read.
**Coverage caveat:** doc plane of a compiled binary; behavioral claims rest on shipped API documentation, checked `no_recorded_issue` by check_index_coverage this pass.

## Get live surrounding code
**Retrieve:** executed live this pass:
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-dotmemory",
  query: "SysTools connection server descriptor stream", limit: 6 });
// → JetBrains.Profiler.Windows.SysTools.doc @ JetBrains.Profiler.Windows.SysTools.xml :2-270;
//   member text (:44-95) read directly from the cited ranges.
```

## Verdict
Adopt the opaque typed-descriptor handoff (`{transport-type, id}` pairs instead of concrete connection objects) and split teardown into Break/Close verbs at the interface level. Adapt the Type enum to your platform's transport set. Omit the Windows-only anon-pipe handle spelling if your platform lacks it; keep HumanReadable for diagnostics.
