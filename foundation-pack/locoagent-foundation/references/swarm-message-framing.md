<!-- capsule-v2 -->
# Teammate message framing — why are teammate messages wrapped in XML before becoming prompts, and which source escapes wrapping?

**Source:** locoagent (Claude Code CLI fork, MIT), rev `c01bb3f`; Codebase Memory `locoagent`. **Question:** how does an in-process teammate's prompt stream preserve the same message identity semantics as tmux teammates' transcript output?

## formatAsTeammateMessage XML wrapper + user-message exception
**Path/Symbol:** `src/utils/swarm/inProcessRunner.ts:formatAsTeammateMessage` (:457-466), application sites :1006-1012 (initial prompt as 'team-lead'), :1363-1408 (wait-result switch); addendum `src/utils/swarm/teammatePromptAddendum.ts:TEAMMATE_SYSTEM_PROMPT_ADDENDUM` (:8-18).
**Signature:** `(from: string, content: string, color?: string, summary?: string) => string` producing `<teammate-message teammate_id="..." color="..." summary="...">`.
**Data Shape:** TEAMMATE_MESSAGE_TAG from constants/xml; attributes omitted when undefined.

### Decisive source
```ts
/**
 * Formats a message as <teammate-message> XML for injection into the conversation.
 * This ensures the model sees messages in the same format as tmux teammates.
 */
function formatAsTeammateMessage(from, content, color?, summary?) {
  const colorAttr = color ? ` color="${color}"` : ''
  const summaryAttr = summary ? ` summary="${summary}"` : ''
  return `<${TEAMMATE_MESSAGE_TAG} teammate_id="${from}"${colorAttr}${summaryAttr}>\n${content}\n</${TEAMMATE_MESSAGE_TAG}>`
}
```
Wait-switch rule (:1388-1391): "Messages from the user should be plain text (not wrapped in XML) / Messages from other teammates get XML wrapper for identification" — `if (waitResult.from === 'user') { currentPrompt = waitResult.message }`.

**Flow:** initial leader prompt arrives pre-wrapped with from='team-lead' + description as summary → every subsequent mailbox/task-list/shutdown prompt re-wrapped by origin (user messages EXEMPT and never double-recorded to task.messages because injectUserMessageToTeammate already added them) → system prompt = full main prompt + TEAMMATE_SYSTEM_PROMPT_ADDENDUM teaching SendMessage-or-invisibility ("Just writing a response in text is not visible to others on your team - you MUST use the SendMessage tool") → custom agent definitions append `\n# Custom Agent Instructions\n...`; 'replace' mode bypasses everything.
**Invariant:** ONE canonical wire format per sender class so downstream parsers (and the model) can attribute messages identically across execution modes; user input is the only unwrapped channel.
**Probe:** coverage caveat (no direct tests). Deterministic probes: `grep -n 'same format as tmux teammates' src/utils/swarm/inProcessRunner.ts` (:455); `grep -n 'MUST use the SendMessage tool' src/utils/swarm/teammatePromptAddendum.ts` (:15).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "formatAsTeammateMessage TEAMMATE_SYSTEM_PROMPT_ADDENDUM appendTeammateMessage", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt sender-typed message framing with exactly one exempt human channel; adapt tag names; omit the addendum if your agents have native messaging tools.
