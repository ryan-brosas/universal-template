<!-- capsule-v2 -->
# Surface-gated failure effects — when does a failed channel run owe the user a visible "Something went wrong"?

**Source:** copilotkit MIT `main@e9387e04835545c45744b791aee7c9c03520be31`; Codebase Memory `ext-copilotkit`. **Question:** A handler crashed mid-delivery — which surfaces must get an explicit failure message, and which must stay silent?

## Three-gate ladder shouldSendGenericFailure + terminal-status classification
**Path/Symbol:** `packages/channels-intelligence/src/delivery-transport.ts` — error path in `claimAndHandle` (:1163-1195); `shouldSendGenericFailure` (:1800-1823); `PreparedChannelDelivery.surfaceKind` (:93-104); `ChannelProviderDeliveryError` (:140-171); `safeChannelErrorMetadata` (:1289+).
**Signature:** `function shouldSendGenericFailure(delivery: PreparedChannelDelivery, claimedDelivery: ClaimedChannelDelivery): boolean`; effect sent via `claimedDelivery.effect("expected_response_failure", {kind: adapter==="slack" ? "slack.message.create" : "teams.message.create", text:"Something went wrong"}, { charge: false })`.
**Data Shape:** `surfaceKind` ∈ `direct_message | app_mention | message | personal | mention | ambient | interaction | welcome | reaction | file_consent`; terminal status chosen by `hasProviderOutput()`.

### Decisive source
```typescript
} catch (error) {
  if (!isChannelDeliveryTerminatedError(error) && !claimedDelivery.isSuperseded()) {
    if (shouldSendGenericFailure(delivery, claimedDelivery)) {
      await claimedDelivery.effect("expected_response_failure",
        { kind: delivery.adapter === "slack" ? "slack.message.create" : "teams.message.create",
          text: "Something went wrong" },
        { charge: false })                       // failures are never metered
        .catch(() => undefined);
    }
    await claimedDelivery.terminal({
      status: claimedDelivery.hasProviderOutput() ? "failed" : "failed_before_output",
      code: "runtime_handler_failed",
    }).catch(() => undefined);
  }
  this.options.log?.("channel delivery handler failed", {
    deliveryId, ...safeChannelErrorMetadata(error),
  });
}
```

**Flow:** handler throws → skip everything if the delivery ALREADY terminated (branded `ChannelDeliveryTerminatedError`) or was superseded (the newer claim owns the user now) → three-gate ladder decides the courtesy message: (1) the handler explicitly attempted visible output (`hasExpectedProviderOutput`) ⇒ always apologize; (2) else promised-reply surfaces (`direct_message`, `app_mention`, `personal`, `mention`, `interaction`, `welcome`) ⇒ apologize; (3) else input-shape fallback: welcome/interaction inputs or a text message where `operation.mentioned` is true ⇒ apologize; ambient/message/reaction/file-consent stay SILENT → always classify the terminal: any provider packet already applied ⇒ `failed`, else `failed_before_output` (this is why stream.stop is excluded from `providerOutputApplied`) → the failure effect itself is unmetered and best-effort.
**Invariant:** Supersession and prior termination ALWAYS outrank the generic apology — double-messaging a thread that a newer runtime already answered is worse than silence. The three-gate ladder means "silent" surfaces can still apologize when the handler itself promised output (gate 1) or the user @mentioned the bot (gate 3) — silence is about NOT interrupting ambient streams, never about hiding acknowledged failures. The transcript-failure path mirrors the same gates (generic for DM/app-mention, silent for ambient — tests :213-269).
**Probe:** `packages/channels-intelligence/src/delivery-transport.test.ts` :353 "interaction handler failure sends the generic provider error"; :379 "ambient handler failure is silent until developer output is expected"; :1264 "still sends a failed terminal when complete terminal fails"; :1430 "does not count stream.stop alone as provider output". Deterministic anchor `grep -n "Something went wrong" packages/channels-intelligence/src/delivery-transport.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-copilotkit", query: "shouldSendGenericFailure surfaceKind failed_before_output safeChannelErrorMetadata", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt surface-conditioned failure messaging plus output-aware terminal classification for any chat channel. Adapt the message text and surface vocabulary to your providers. Omit the charge:false on failure effects and you bill users for your own crashes.
