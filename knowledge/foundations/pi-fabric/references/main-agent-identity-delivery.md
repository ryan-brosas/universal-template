<!-- capsule-v2 -->
# Main-agent identity & delivery — how does any process in the fleet address the root Main agent without impersonating it?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** given hosts spawned as actors, recursive agents, or plain mains, who is "Main" for this process, when may it message Main directly, and how does the message survive the host boundary?

## Connected graph-selected seam
**Path/Symbol:** `src/main-agent.ts` whole file (172L): `MAIN_AGENT_ALIAS` (:5), `resolveFabricIdentity` (:53-80), `serializableData` (:85-92), `MainAgentController` (:94-172) — `matches` (:105-108), `info` (:110-131), `deliverUser` (:133-140), `deliverAgent` (:142-171).
**Signature:** `resolveFabricIdentity(sessionId, environment = process.env)` → `{identity: MeshIdentity, mainAgentId: string}`; `deliverUser(message, delivery)` / `deliverAgent({from, message, delivery, triggerTurn?, data?})` → `{queued: true, messageId, routed}`; both THROW when `local === false`.
**Data Shape:** `FabricMainAgentInfo {id, name: "Main", kind: "main", status: "idle"|"running"|"remote", runner: "pi", transport: "host", cwd?, sessionId?, model?, thinking?, startedAt?, updatedAt, pendingMessages, local}`; `FabricAgentMessageDelivery = "steer" | "followUp"`.

### Decisive source
```ts
const actorId = environment.PI_FABRIC_ACTOR_ID?.trim();
const parentAgentId = environment.PI_FABRIC_PARENT_RUN?.trim();
const identity: MeshIdentity = actorId
  ? { id: actorId, name: environment.PI_FABRIC_ACTOR_NAME?.trim() || actorId.slice(0, 8), kind: "actor", sessionId }
  : parentAgentId
    ? { id: parentAgentId, name: environment.PI_FABRIC_AGENT_NAME?.trim() || parentAgentId.slice(0, 8), kind: "agent", sessionId }
    : { id: `session:${sessionId}`, name: "main", kind: "main", sessionId };
const inheritedMainAgentId = environment.PI_FABRIC_MAIN_AGENT_ID?.trim();
return {
  identity,
  mainAgentId: inheritedMainAgentId || (identity.kind === "main" ? identity.id : `session:${sessionId}`),
};
```

**Flow:** At `FabricState.initialize`, the env ladder decides WHO this process is (actor beats recursive-agent beats plain main; display names fall back to the first 8 chars of the id, never the raw id). `mainAgentId` is inherited via `PI_FABRIC_MAIN_AGENT_ID` so a child knows who Main is even though it is NOT Main. `MainAgentController.local = (identity.kind === "main" && identity.id === mainAgentId)` — only a genuine root both resolves and equals Main, so only it may deliver. `deliverUser` trims + requires non-empty, routes via `pi.sendUserMessage(text, {deliverAs})`; `deliverAgent` builds an XML envelope `<fabric-agent-message from_name=… from_id=… from_kind=…>` with `escapeXmlText` around the body, optional `<data>` line carrying JSON-stringified escaped payload, plus machine-readable `details {id, from: structuredClone(...), delivery, triggerTurn ?? true, data?}` sent through `pi.sendMessage(..., {deliverAs, triggerTurn})`.
**Invariant:** (1) identity precedence is FIXED: `PI_FABRIC_ACTOR_ID` > `PI_FABRIC_PARENT_RUN` > session-main fallback — a process with both vars set is an actor. (2) A child's own identity is NEVER its `mainAgentId`; only `identity.kind === "main"` yields `identity.id === mainAgentId` ⇒ `local === true`. (3) Both delivery methods throw `Main agent … is owned by another Fabric process` when `!local` — direct delivery from a non-owner is impossible by construction; remote peers must go through mesh commands. (4) Message text is XML-escaped INTO the envelope while `details.from` carries the RAW identity via `structuredClone` — later mutation of the caller's object cannot rewrite the persisted audit. (5) Unserializable `data` degrades to the `{fabricUnserializable: true}` sentinel instead of throwing mid-send. (6) `triggerTurn` defaults TRUE (`?? true`) — forgetting the `??` silently turns steering into background queueing. (7) `matches()` accepts the stable alias `"main"` OR the exact resolved id, so UIs can target Main without knowing the session id.
**Probe:** `tests/main-agent.test.ts:9` ("resolves root, recursive-agent, and actor identities without losing the root Main target" — asserts all three ladder outcomes byte-exact), `:54` ("reports live Main state and preserves user versus agent message semantics" — model/thinking/pendingMessages only when local; XML-escaped content; `structuredClone`d from), `:140` ("rejects direct delivery from a process that does not own Main" — throws `/owned by another/`, info reports `status: "remote"` with NO model/cwd/startedAt fields).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "resolveFabricIdentity MainAgentController deliverAgent deliverUser matches", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-value identity resolution (`identity`, `mainAgentId`) with env-var inheritance and the local-gated delivery pair; adapt var names and the custom message type (`pi-fabric-agent-message`) to your host. Never let a non-owner process synthesize messages to Main — route them through the transport's command plane instead.
