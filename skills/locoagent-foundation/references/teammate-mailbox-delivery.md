<!-- capsule-v2 -->
# Teammate mailbox delivery — two sources, protocol-message filtering, dedup, and build-before-mark ordering?

**Source:** locoagent (Claude Code CLI fork, rev `c01bb3f`); Codebase Memory `locoagent`. **Question:** delivering swarm messages exactly once while leaving structured protocol messages for their proper handlers.

## getTeammateMailboxAttachments
**Path/Symbol:** `src/utils/attachments.ts:getTeammateMailboxAttachments` (:3520-3769), `getTeamContextAttachment` (:3771-3805), session_memory skip at :898-910.
**Signature:** `(toolUseContext) → Promise<Attachment[]>`; gated `isAgentSwarmsEnabled() && USER_TYPE === 'ant'`.
**Data Shape:** reads TWO sources — file mailbox (`readUnreadMessages(agentName, teamName)`) + `appState.inbox` pending; emits single `teammate_mailbox { messages[] }`; agent name resolved via viewed-teammate → env → team-lead lookup.

### Decisive source
```ts
// Filter out structured protocol messages (permission requests/responses,
// shutdown messages, etc.) — these must be left unread for useInboxPoller to
// route to their proper handlers ... Without filtering, attachment generation
// races with InboxPoller: whichever reads first marks all messages as read,
// and if attachments wins, protocol messages get bundled as raw LLM context
// text instead of being routed to their UI handlers.
const unreadMessages = allUnreadMessages.filter(m => !isStructuredProtocolMessage(m.text))
// ...
// Build the attachment BEFORE marking messages as processed
// This prevents message loss if any operation below fails
```

**Flow:** resolve identity (viewing-teammate override for transcript inspection) → read file mailbox → FILTER structured protocol messages OUT of the mark-as-read set → merge with AppState.inbox pendings keyed `${from}|${timestamp}|${text.slice(0,100)}` (dedups the poller/attachment race where both sources saw the same file message) → collapse idle notifications per agent keeping ONLY latest → BUILD the attachment object → then mark non-structured mailbox messages read by predicate → then leader-side shutdown_approved side effects (remove teammate from team file, unassign tasks, update AppState) → LAST mark inbox items 'processed'. In-process teammates NEVER read appState.inbox ("contains the LEADER's queued messages... self-echo from broadcasts"); the session_memory forked agent skips mailbox entirely or it steals the leader's DMs as ephemeral attachments (:900-904).
**Invariant:** mark-after-build for BOTH stores (crash between = duplicate delivery, never loss); protocol messages stay UNREAD so their real consumers see them; identity resolution must account for who's being VIEWED not just who's running.
**Probe:** no upstream test (coverage caveat); race rationale pinned verbatim :3584-3589. Deterministic probe: `sed -n '3676,3696p' src/utils/attachments.ts` shows build→mark order.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "getTeammateMailboxAttachments isStructuredProtocolMessage markMessagesAsReadByPredicate", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt dual-source dedup + predicate-scoped read-marking + build-before-mark; adapt transports; omit ant-gating. Porting trap: marking everything read on delivery permanently swallows permission-request protocol messages into chat text; marking before building loses messages if any later step throws.
