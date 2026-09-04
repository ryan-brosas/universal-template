<!-- capsule-v2 -->
# WCF agent channel endpoint matrix — how does an unprivileged host talk to out-of-process profiler agents, including the elevated one?

**Source:** JetBrains dotTrace standalone distribution (proprietary distribution; study/reference use only, citations-only), pin `?@?` (not git-managed; identity = root + Codebase Memory generation 2026-08-24T13:55:36Z); Codebase Memory `jetbrains-dottrace`. **Question:** What is the wire contract between the profiler UI/host and its out-of-process agents (RemoteAgent, ElevationAgent), when every doc plane for those assemblies ships empty?

## One WCF contract, four client endpoints, transport chosen by topology — and only the privileged channel keeps authentication
**Path/Symbol:** `JetBrains.Profiler.Windows.RemoteAgent.dll.config` :3-40 (`<system.serviceModel>`); counterpart empty doc stubs `JetBrains.Profiler.Windows.RemoteAgent.xml` / `…Remotable.Agent.xml` (:6-7, `<members/>`).
**Signature:** all four `<endpoint>` entries share ONE contract `JetBrainsAgentContract` + one behavior `JetBrainsAgentBehavior`; they differ only in binding/bindingConfiguration/name: `JetBrainsRemoteAgentClient_{WSHttp,NetTcp,NetNamedPipe}` and `JetBrainsElevationAgentClient_NetNamedPipe`.
**Data Shape:** every binding sets `maxReceivedMessageSize="2147483647"`, `readerQuotas maxStringContentLength/maxArrayLength/maxBytesPerRead="2147483647"`, `openTimeout/sendTimeout/closeTimeout="00:01:00"`; the shared behavior raises `dataContractSerializer maxItemsInObjectGraph="2147483647"`. Security postures SPLIT: wsHttp and netTcp declare `<security mode="None" />` explicitly (:14, :20), the remote-agent named-pipe binding also declares None (:26) — but `JetBrainsElevationAgentBinding_NetNamedPipe` (:28-30) has NO security element at all, keeping WCF's netNamedPipe default (Transport = Windows named-pipe identity) ON.

### Decisive source
```xml
<!-- RemoteAgent.dll.config :5-8 — the whole fleet on one contract -->
<endpoint contract="JetBrainsAgentContract" … name="JetBrainsRemoteAgentClient_WSHttp"
          binding="wsHttpBinding" bindingConfiguration="JetBrainsRemoteAgentBinding_WSHttp" />
<endpoint contract="JetBrainsAgentContract" … name="JetBrainsRemoteAgentClient_NetTcp" … />
<endpoint contract="JetBrainsAgentContract" … name="JetBrainsRemoteAgentClient_NetNamedPipe" … />
<endpoint contract="JetBrainsAgentContract" … name="JetBrainsElevationAgentClient_NetNamedPipe"
          binding="netNamedPipeBinding" bindingConfiguration="JetBrainsElevationAgentBinding_NetNamedPipe" />
```

**Flow:** host picks a channel by deployment shape — cross-machine control rides wsHttp/netTcp, same-machine rides named pipes; the ELEVATED agent (see `elevation-agent-uac-manifest-split`) is always a local admin child, so it gets a dedicated named-pipe-only endpoint whose binding silently retains OS pipe-identity security while every remote-agent channel runs plaintext.
**Invariant:** quota ceilings are all `int.MaxValue` because attach/snapshot payloads are snapshot-sized — a WCF config for fat local payloads must raise message size AND reader quotas AND serializer graph count together or transfers fail piecemeal; authentication follows privilege, not transport: unprivileged remote channels may be explicit-None, but the channel that can change system ACLs must keep its default OS-level identity check. Named-pipe bindings with explicit `security mode="None"` are possible and here deliberate.
**Probe:** executed this pass against the shipped file: exact `int.MaxValue` census via `grep -o | wc -l` = **17** (= 4 × `maxReceivedMessageSize` + 4 bindings × 3 readerQuota attrs + 1 × `maxItemsInObjectGraph`); `grep -n "security"` = exactly :14/:20/:26, proving the elevation binding alone carries none; `grep -c "<endpoint "` = 4.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-dottrace",
  query: "RemoteAgent remote agent configuration", limit: 50 });
// → jetbrains-dottrace.JetBrains.Profiler.Windows.RemoteAgent.doc @ …RemoteAgent.xml :2-8
//   (EMPTY members stub confirmed live — the .config file is not indexed at all:
//    check_index_coverage freshness=not_tracked) — so the decisive evidence above
//    is a direct file read, correctly scoped by MCP to prove the docs are empty.
```

## Verdict
Adopt the matrix when splitting a tool into unprivileged UI + privileged/local helper processes: one shared service contract over multiple transport endpoints, per-endpoint binding configs, quotas sized for your fattest payload, security decided per channel (default-on only where the peer is privileged). Adapt transports to your platform (named pipes ↔ Unix sockets). Omit WCF itself if greenfield — port the *policy*: elevation channel authenticated, data channels cheap, everything else identical.
