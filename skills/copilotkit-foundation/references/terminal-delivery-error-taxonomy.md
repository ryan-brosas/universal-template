<!-- capsule-v2 -->
# terminal-delivery-error-taxonomy

## Source
- Repo: `copilotkit`
- Path: `packages/channels-core/src/delivery-error.ts`
- Symbol: `ChannelDeliveryTerminatedError` / `isChannelDeliveryTerminatedError`
- Lines: 7-65
- Commit: `e9387e04835545c45744b791aee7c9c03520be31`
- Graph Node: `ext-copilotkit.packages.channels-core.src.delivery-error.ChannelDeliveryTerminatedError`

## Signature & Data Shape
```typescript
export interface ChannelDeliveryErrorDetails {
  readonly category: "validation";
  readonly provider: "slack" | "teams";
  readonly operation: string;
  readonly effectKind: string;
  readonly providerCode: "invalid_arguments" | "invalid_blocks";
  readonly validationMessages: readonly string[];
  readonly retryable: false;
  readonly deliveryId: string;
}

export class ChannelDeliveryTerminatedError extends Error {
  readonly [CHANNEL_DELIVERY_TERMINATED] = true;
  readonly details?: ChannelDeliveryErrorDetails;
}
```

## Decisive Source Excerpt
```typescript
const CHANNEL_DELIVERY_TERMINATED = Symbol.for(
  "copilotkit.channels.deliveryTerminated",
);
const CHANNEL_DELIVERY_ERROR_DETAILS = Symbol.for(
  "copilotkit.channels.deliveryErrorDetails",
);

export class ChannelDeliveryTerminatedError extends Error {
  readonly [CHANNEL_DELIVERY_TERMINATED] = true;
  readonly [CHANNEL_DELIVERY_ERROR_DETAILS]?: ChannelDeliveryErrorDetails;
  readonly details?: ChannelDeliveryErrorDetails;

  constructor(
    message: string,
    options?: ChannelDeliveryTerminatedErrorOptions,
  ) {
    super(message, options);
    this.name = "ChannelDeliveryTerminatedError";
    if (isChannelDeliveryErrorDetails(options?.details)) {
      this.details = options.details;
      this[CHANNEL_DELIVERY_ERROR_DETAILS] = options.details;
    }
  }
}

export function isChannelDeliveryTerminatedError(
  error: unknown,
): error is ChannelDeliveryTerminatedError {
  return (
    typeof error === "object" &&
    error !== null &&
    (error as { [CHANNEL_DELIVERY_TERMINATED]?: unknown })[
      CHANNEL_DELIVERY_TERMINATED
    ] === true
  );
}
```

## Flow
1. Tag terminal channel delivery errors with global `Symbol.for("copilotkit.channels.deliveryTerminated")`.
2. Inspect errors using `isChannelDeliveryTerminatedError` across package boundaries and bundled modules.
3. Validate error diagnostics (`category: "validation"`, `providerCode`, `retryable: false`).
4. Prevent tool handlers from converting terminal delivery failures into regular model tool return values.
5. Immediately terminate the agent turn to prevent emitting further events to a closed or failed delivery channel.

## Invariant
Terminal delivery errors must be identified via global symbol branding rather than class prototype checks to survive duplicated packages, and must immediately abort agent turn execution rather than feeding failure messages back to the LLM.

## Direct-Test Probe
- File: `packages/channels-core/src/canonical-run-loop.test.ts`
- Lines: 450-490
- Assertion: `isChannelDeliveryTerminatedError(err) === true`

## Graph Query
```bash
codebase-memory-mcp cli search_graph '{"project":"ext-copilotkit","query":"ChannelDeliveryTerminatedError CHANNEL_DELIVERY_TERMINATED"}'
```

## Verdict
Adopt global symbol-branded error taxonomy for cross-package terminal delivery error handling.
