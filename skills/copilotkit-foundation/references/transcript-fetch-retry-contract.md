<!-- capsule-v2 -->
# Transcript client — why exactly three attempts, and why does an invalid 200 kill the fetch but a 429 gets another try?

**Source:** copilotkit MIT `main@e9387e04835545c45744b791aee7c9c03520be31`; Codebase Memory `ext-copilotkit`. **Question:** How is the conversation transcript fetched for a delivery, and what is the precise retry/failure classification contract a porter must preserve?

## Fixed-3-attempt ladder with asymmetric failure classes
**Path/Symbol:** `packages/channels-intelligence/src/delivery-transcript.ts:ChannelDeliveryTranscriptClient.fetchTranscript` (:203-272); `parseTranscript` (:158-180), `parseError` (:182-197), `ChannelDeliveryTranscriptError` (:53-62); message/file validators :97-156; consumed by `ClaimedChannelDelivery.getTranscript` memoizer (delivery-transport.ts :530-542).
**Signature:** `async fetchTranscript(deliveryId: string): Promise<ChannelDeliveryTranscript>`; error carries `(code: string, retryable: boolean, attempts: number)`.
**Data Shape:** transcript = ≤100 messages × (≤100 files each), `logicalMessageId`/`revisionId` are `pid_v1_*`, `messageRef.id` is `pref_v1_*`, `occurredAt` strict ISO, `truncation {messageLimit, byteLimit, omittedMessageCount}` required; GET `/api/channels/deliveries/:id/transcript`.

### Decisive source
```typescript
for (let attempt = 1; attempt <= 3; attempt += 1) {
  let response: Response;
  try {
    response = await fetchImpl(url, { method: "GET", headers: { authorization: `Bearer ...` } });
  } catch {
    if (attempt < 3) continue;                    // network throw ⇒ silent retry
    throw new ChannelDeliveryTranscriptError("CHANNEL_TRANSCRIPT_RETRYABLE", true, attempt);
  }
  try { body = await response.json(); }
  catch {
    throw new ChannelDeliveryTranscriptError("CHANNEL_TRANSCRIPT_RESPONSE_INVALID", false, attempt);
  }
  if (response.ok) {
    const transcript = parseTranscript(body);
    if (!transcript) throw new ChannelDeliveryTranscriptError("CHANNEL_TRANSCRIPT_RESPONSE_INVALID", false, attempt);
    return transcript;
  }
  const error = parseError(body, response.status); // retryable defaults to 429 || status >= 500
  if (!error.retryable || attempt === 3) throw new ChannelDeliveryTranscriptError(error.code, error.retryable, attempt);
}
```

**Flow:** up to three attempts → transport exceptions retry SILENTLY then surface `RETRYABLE`; malformed JSON or a 200 whose body fails exact-field validation throws NON-retryable `RESPONSE_INVALID` IMMEDIATELY; HTTP errors classify via body `{code?, retryable?}` with fallback `retryable = status === 429 || status >= 500` and retry only while the server says so and attempts remain → every exit is a typed error carrying its attempt count.
**Invariant:** The asymmetry is load-bearing: a well-formed-but-wrong payload means the SERVER's data contract is broken — retrying cannot fix it and may re-feed corrupt conversation history into the agent context; rate-limit/5xx mean the same correct request can succeed later. Callers memoize per delivery (`transcriptPromise ??=`) so retries never duplicate agent-visible history either.
**Probe:** `packages/channels-intelligence/src/delivery-transcript.test.ts` (7 tests over parse/retry classes); `packages/channels-intelligence/src/delivery-transport.test.ts` :213 "transcript failure posts the generic unmetered error for an app mention". Deterministic anchor `grep -n "attempt <= 3" packages/channels-intelligence/src/delivery-transcript.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-copilotkit", query: "fetchTranscript parseTranscript ChannelDeliveryTranscriptError", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-class ladder (transport-retry / payload-invalid-fail-fast / status-gated-retry) for any read-model fetch feeding LLM context. Adapt bounds to your API. Omit the 200-body validation and a schema drift poisons agent memory silently.
