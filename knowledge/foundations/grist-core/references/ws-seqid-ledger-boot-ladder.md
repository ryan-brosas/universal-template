<!-- capsule-v2 -->
# ws-seqid-ledger-boot-ladder — How are outbound messages buffered for a disconnected client, and when does buffering flip into destroying the client?

**Source:** GristLabs grist-core Apache-2.0 `main@b83224bbe9c8`; Codebase Memory `grist-core`. **Question:** What exactly does the server hold for a disconnected client, and at what thresholds must it stop holding and boot?

## Missed-message ledger with boot ladder
**Path/Symbol:** `_missedMessages: Map<number,string>` + `_missedMessagesTotalLength` (`app/server/lib/Client.ts:91–92`); constants :22–26; enqueue in `sendMessage` :293–309; drop in `_dropMissedMessages` :566–574; window-start watermark field :100–102.
**Signature:** queue guard `this._missedMessages.size < clientMaxMissedMessages && this._missedMessagesTotalLength + message.length <= clientMaxMissedBytes` with `clientMaxMissedMessages = 100`, `clientMaxMissedBytes = 1_000_000`.
**Data Shape:** per-Client Map seqId→JSON string; seqIds stamped monotonically in sendMessage (:269 `const seqId = this._nextSeqId++`); dual budget count+bytes; `_missedMessagesWindowStart` distinguishes "never held" from "held once".

### Decisive source
```ts
if (this._missedMessages.size < clientMaxMissedMessages &&
    this._missedMessagesTotalLength + message.length <= clientMaxMissedBytes) {
  // Queue up the message.
  this._missedMessages.set(seqId, message);
  this._missedMessagesTotalLength += message.length;
} else {
  // Too many messages queued. Boot the client now, to make it reset when/if it reconnects.
  this._log.warn(null, "sendMessage: too many messages queued; booting client");
  this.destroy();
}
```

**Flow:** send fails or no socket ⇒ ledger.set(seqId, message), length += message.length → resume collects the contiguous run [firstNeeded, _nextSeqId): any hole ⇒ undefined ⇒ needReload → after handover or destroy, `_dropMissedMessages(bound)` deletes keys < bound AND raises `_missedMessagesWindowStart = Math.max(windowStart, bound)` (max-only watermark, never moves back) → over EITHER budget ⇒ boot immediately: destroy() closes docs, drops ledger through _nextSeqId, unregisters from Comm; client resets on next connect.
**Invariant:** budgets are CHECK-BEFORE-INSERT on BOTH count and bytes; boot is the safety valve — an absent client must not grow server memory without bound, destruction beats unbounded retention. The contiguous-run contract means partial recovery is never attempted: a single missing seqId forces reload rather than delivering everything after the hole.
**Probe:** `test/server/Comm.ts:364` ("should forward missed responses when a server send fails") + :367 ("when a server send is queued") — buffered answers delivered intact on reconnect.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "_dropMissedMessages", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dual-budget check-before-insert ledger + max-only window watermark + boot-instead-of-grow ladder. Adapt thresholds to your memory profile. Omit Grist's docFD coupling (destroy() also closeAllDocs) unless porting sessions too.
