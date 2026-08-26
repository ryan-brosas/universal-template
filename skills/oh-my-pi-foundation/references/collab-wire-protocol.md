<!-- capsule-v2 -->
# Collab wire protocol — how a live-session collab host/guest/relay speak over the wire

**Source:** oh-my-pi (MIT) `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** How does the OMP collab live-session protocol shape its messages, session entries, events, frames, envelope, and link so a porter can build a compatible host/guest/relay without re-deriving the contract?

## Dependency-free wire shapes
**Path/Symbol:** `packages/wire/src/index.ts` (whole file, 444L).
**Signature:** pure exported interfaces + consts — no runtime logic beyond constants. Consumers (`@oh-my-pi/pi-coding-agent` `src/collab/protocol.ts`, browser + test clients) import this package instead of depending on the coding-agent runtime; conformance is asserted type-only in `packages/coding-agent/test/collab/web-wire.types.ts`.
**Data Shape:** discriminated unions keyed on a `type`/`t` literal. Unknown variants arrive as plain JSON; every consumer `switch` keeps a tolerant `default:` branch and casts at the JSON boundary. Constants: `COLLAB_PROTO=3`, `INTENT_FIELD="i"`, `ENVELOPE_HEADER_LENGTH=4`, `ROOM_ID_BYTES=16`, `ROOM_KEY_BYTES=32`, `WRITE_TOKEN_BYTES=16`, `DEFAULT_RELAY_URL="wss://my.omp.sh"`, `DEFAULT_SHARE_URL="https://my.omp.sh/s"`, `COLLAB_PROMPT_MESSAGE_TYPE="collab-prompt"`.

### Decisive source
```ts
export type WireFrame = GuestFrame | HostFrame;
// GuestFrame: hello{proto,name,writeToken?} | prompt{text,images?} | ui-response{reqId,value?}
//            | abort | agent-cmd{cmd:chat|kill|revive,agentId,text?} | fetch-transcript{reqId,agentId,fromByte}
// HostFrame: welcome{proto,header,state,agents,entryCount,readOnly?} | snapshot-chunk{entries,final}
//          | entry{entry} | event{event} | state{state} | bus{channel,data} | agents{agents}
//          | ui-request{request} | ui-request-end{reqId} | transcript{reqId,text,newSize,error?} | bye{reason} | error{message}
export const COLLAB_PROTO = 3; // v1: welcome carried full entries inline; v2: snapshot-chunk frames; v3: ui-request/response
export const INTENT_FIELD = "i"; // intent-tracing param (e.g. prompt explanation/reasoning)
// Envelope: [4B uint32 BE peerId][sealed payload]; AES-256-GCM room key = seal key for every frame.
// Full link: base64url(key ∥ writeToken); view link: bare key. writeToken proves prompt/abort/agent-cmd capability.
```

**Flow:** guest connects to relay with `<roomId>.<key>` link → sends `hello{proto,writeToken?}` → host replies `welcome` (metadata only: header/state/agents/entryCount) then streams the transcript in `snapshot-chunk` frames (byte-bounded, last carries `final:true`) → thereafter `entry`/`event`/`state`/`agents`/`bus`/`ui-request` frames; guest answers `ui-response`; relay sends unencrypted TEXT control messages (`peer-joined`/`peer-left` to host, `room-closed` to guest).
**Invariant:** protocol version is carried in `hello` and the host REJECTS mismatches (a guest predating the ui-request grammar would silently drop `ui-request` and hang the host's asks forever — so it must be rejected at hello). Peers without a valid `writeToken` are marked read-only and their mutating frames rejected. `message_update` carries the FULL accumulating partial message — no delta tracking needed.
**Probe:** `packages/wire/test/constants.test.ts` (18L) — pins `COLLAB_PROTO=3`, `COLLAB_PROMPT_MESSAGE_TYPE="collab-prompt"`, `ENVELOPE_HEADER_LENGTH=4`, `ROOM_ID_BYTES=16`, `DEFAULT_RELAY_URL="wss://my.omp.sh"`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "WireFrame COLLAB_PROTO INTENT_FIELD session entry event", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dependency-free discriminated-union wire shapes (content blocks, messages, session entries, events, frames), the envelope `[4B peerId][AES-GCM seal]` + link `key∥writeToken` split, and the version-reject-at-hello + tolerant-default-switch + full-message-update invariants; adapt relay/share URLs, room-key bytes, and the exact entry/event variant set to the host; omit nothing here — this package is pure portable contract. Direct test `constants.test.ts` pins only the constants; the message/entry/event/frame shapes are type-only (conformance asserted type-only in `coding-agent/test/collab/web-wire.types.ts`), so shape claims are source-grounded with that type-only caveat.
