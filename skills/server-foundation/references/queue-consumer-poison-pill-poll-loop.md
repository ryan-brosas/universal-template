<!-- capsule-v2 -->
# Queue consumer poison-pill poll loop — how do I drain a notification queue into a push fabric without a poison message or shutdown hanging the host?

**Source:** Bitwarden server AGPL-3.0 `main@ac309aa19ed351406a56032d5f26a7a9a99f4abd`; Codebase Memory `server`. **Question:** What is the receive-side loop's start gate, redelivery bound, and stop ladder?

## AzureQueueHostedService
**Path/Symbol:** `src/Notifications/AzureQueueHostedService.cs:18–116` (`StartAsync` :30–36, `StopAsync` :38–52, `ExecuteAsync` :58–115); contrast class `src/Notifications/HeartbeatHostedService.cs:9–59`; wiring `src/Notifications/Startup.cs:71–82`.
**Signature:** `public Task StartAsync(CancellationToken)` / `public async Task StopAsync(CancellationToken)` / `private async Task ExecuteAsync(CancellationToken)`.
**Data Shape:** keyed `QueueClient("notifications")` resolved from `IServiceProvider`; messages are raw JSON envelope strings; `ReceiveMessagesAsync(32)` batch; per-message `MessageId`/`PopReceipt`/`DequeueCount`.

### Decisive source
```csharp
public Task StartAsync(CancellationToken cancellationToken)
{
    if (_globalSettings.SelfHosted ||
        !CoreHelpers.SettingHasValue(_globalSettings.Notifications?.ConnectionString))
    {
        return Task.CompletedTask;   // inert: no task started at all
    }
    _cts = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
    _executingTask = ExecuteAsync(_cts.Token);
    return _executingTask.IsCompleted ? _executingTask : Task.CompletedTask;
}
// …inside ExecuteAsync, per dequeued message:
catch (Exception e)
{
    _logger.LogError(e, "Error processing dequeued message: {MessageId} x{DequeueCount}.", …);
    if (message.DequeueCount > 2)
    {
        await queueClient.DeleteMessageAsync(message.MessageId, message.PopReceipt, cancellationToken);
    }
}
// …StopAsync:
_cts?.Cancel();
await Task.WhenAny(_executingTask, Task.Delay(-1, cancellationToken));
cancellationToken.ThrowIfCancellationRequested();
```

**Flow:** start gate ⇒ service registers unconditionally in DI but does nothing when self-hosted or unconfigured (self-hosted uses the relay path instead). Loop: poll up to 32 messages; process each (hand JSON to `HubHelpers.SendNotificationToHubAsync`); delete on success; on exception log id+dequeue-count and force-delete once `DequeueCount > 2` — a bounded at-least-once policy where every message gets ≈3 delivery attempts before being dropped as poison. Empty batch ⇒ 5 s delay through an injected `TimeProvider`. Outer catches: quiet break on cancellation (`"Task.Delay cancelled during Alpine container shutdown"`), log-and-continue otherwise. Stop: cancel the linked CTS, wait for EITHER loop exit or the host's own token firing (`Task.Delay(-1, cancellationToken)`), then rethrow if the host is what cancelled — bounded graceful stop that never hangs forever but still surfaces forced shutdowns.
**Invariant:** (1) an unconfigured deployment must not even start the loop task (inert-start, not crash); (2) poison isolation is per-message — one bad payload never stops the batch or the loop; (3) delete-after-process gives at-least-once with a dequeue-count ceiling converting unbounded retries into a bounded drop; (4) shutdown waits for the worker OR the host-token race, never both forever. Contrast: `HeartbeatHostedService` shares the identical StopAsync ladder but has NO start gate and NO try/catch around its `Clients.All.SendAsync("Heartbeat")` loop — one transient hub failure silently kills the heartbeat task. Copy the ladder AND the guards together.
**Probe:** routing behavior over this exact loop is exercised live in `test/Notifications.Test/AzureQueuePipelineTests.cs:192–215` via `ChannelQueueClient` (channel-backed `QueueClient` whose `ReceiveMessagesAsync` blocks until a message exists, so tests never hit the 5 s sleep path — see `test/Notifications.Test/ChannelQueueClient.cs:59–86`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.trace_path({ project: "server", function_name: "SendNotificationToHubAsync", direction: "inbound", depth: 2 });
```

## Verdict
Adopt: inert-start gate, per-message try/delete with DequeueCount-ceiling poison drop, TimeProvider-injected idle delay, WhenAny shutdown ladder with host-token rethrow. Adapt: batch size and retry ceiling to your queue's visibility-timeout semantics. Omit: Azure Storage SDK call shapes; the Alpine-specific catch comment.
