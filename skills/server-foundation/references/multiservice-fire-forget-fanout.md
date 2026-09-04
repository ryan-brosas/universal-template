<!-- capsule-v2 -->
# Multi-service fire-and-forget fan-out — how does one notification reach every push engine without failing (or waiting for) the caller?

**Source:** Bitwarden server AGPL-3.0 `main@ac309aa19ed351406a56032d5f26a7a9a99f4abd`; Codebase Memory `server`. **Question:** When domain code awaits a push, what delivery/latency/failure contract do I inherit?

## Fan-out kernel
**Path/Symbol:** `src/Core/Platform/Push/Engines/MultiServicePushNotificationService.cs:38–70` (`PushToServices`, ctor :16–33); sole implementation of `IPushNotificationService`.
**Signature:** `private Task PushToServices(Func<IPushEngine, Task> pushFunc)` / `Task PushAsync<T>(PushNotification<T>) where T : class`.
**Data Shape:** ctor receives `IEnumerable<IPushEngine>` and filters out every `NoopPushEngine` up front (`_services = [.. services.Where(engine => engine is not NoopPushEngine)]`). Empty survivor list ⇒ warning log + immediate `Task.CompletedTask`.

### Decisive source
```csharp
foreach (var service in _services)
{
    Logger.LogDebug("Pushing notification to service {ServiceName}", service.GetType().Name);
#if DEBUG
    var task =
#endif
    pushFunc(service);
#if DEBUG
    tasks.Add(task);
#endif
}

#if DEBUG
return Task.WhenAll(tasks);
#else
return Task.CompletedTask;
#endif
```

**Flow:** caller awaits `PushAsync` → loop invokes each engine's `PushAsync` synchronously up to its first await → in Release the returned Task is discarded and `CompletedTask` returns immediately → engines continue unobserved; only a DEBUG build aggregates via `Task.WhenAll`. Noop engines were already removed at construction, so "no engines" means genuinely nothing configured.
**Invariant:** In Release, an engine throwing synchronously or faulting asynchronously must never propagate to the caller — but it is *unobserved* (no logging of the fault either). Porters who need delivery confirmation or error isolation must add their own wrapper; do not "fix" this into awaited fan-out without accepting the latency change.
**Probe:** `test/Core.Test/Platform/Push/MultiServicePushNotificationServiceTests.cs:32–56` — the only fan-out assertions (`Received(1)` on both fake engines) live inside `#if DEBUG`; their existence proves Release behavior is intentionally unverifiable by tests.
Coverage caveat: file is parse_partial at :53/:57 (both inside the `#if DEBUG` block); both lines read directly from source.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "server", query: "MultiServicePushNotificationService PushToServices fire-and-forget", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt: constructor-time Noop filtering + per-notification broadcast to every surviving engine; empty-engine early return. Adapt: swap the discarded-task posture for a logged-safe wrapper if your host requires failure telemetry (that is an extension of the contract, not a deviation). Omit: DEBUG-only `WhenAll` observability — it is a test affordance, not production behavior.
