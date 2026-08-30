<!-- capsule-v2 -->
# dual-flush-strategy — How is a bounded screenshot trajectory maintained for both long- and short-context models?

**Source:** Agent-S MIT `main@bffdb59c`; Codebase Memory `ext-agent-s`. **Question:** What two different history-pruning strategies run after each turn, and what structure does each assume?

## Flush seam
**Path/Symbol:** `gui_agents/s3/agents/worker.py:Worker.flush_messages` (:90-123); called at :352 after every turn.
**Signature:** `flush_messages(self) -> None` (mutates generator_agent and reflection_agent messages in place).
**Data Shape:** Long-context branch (`engine_type in ["anthropic", "openai", "gemini"]`): messages carry content-part lists with `"type": "image"` parts; keep newest `max_trajectory_length` (default 8) images, delete older image PARTS. Short-context branch: drop whole turns — generator pops index 1 twice ([user, assistant] per round), reflector pops index 1 once.

### Decisive source
```python
# Long-context: prune image PARTS only, walking backwards
img_count = 0
for i in range(len(agent.messages) - 1, -1, -1):
    for j in range(len(agent.messages[i]["content"])):
        if "image" in agent.messages[i]["content"][j].get("type", ""):
            img_count += 1
            if img_count > max_images:
                del agent.messages[i]["content"][j]
# Short-context: pop whole turns from the front (index 0 = system)
if len(self.generator_agent.messages) > 2 * self.max_trajectory_length + 1:
    self.generator_agent.messages.pop(1); self.generator_agent.messages.pop(1)
if len(self.reflection_agent.messages) > self.max_trajectory_length + 1:
    self.reflection_agent.messages.pop(1)
```

**Flow:** turn completes → flush → engine_type routed → long-context keeps all TEXT of every turn but only the latest k screenshots; short-context keeps whole turns up to k rounds and drops the oldest round first.
**Invariant:** (1) Index 0 (system) is never popped; index 1 is always the oldest conversational message. (2) The long-context deletion walks messages backwards while deleting inner list items by index — reversing direction or iterating forwards corrupts indices. (3) The reflection transcript is ALL-USER messages (one per turn, each pairing last action text + new screenshot) — its "2 per round" assumption would be wrong if applied to the generator. (4) max_trajectory_length counts IMAGE turns, not tokens.
**Probe:** `grep -n 'del agent.messages\[i\]\["content"\]\[j\]' gui_agents/s3/agents/worker.py` → :113.
**Probe:** `grep -n 'messages.pop(1)' gui_agents/s3/agents/worker.py` → :119, :120, :123.
**Probe:** `grep -n 'engine_type in \["anthropic", "openai", "gemini"\]' gui_agents/s3/agents/worker.py` → :101.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agent-s", query: "Worker flush_messages s3", limit: 5 });
```

## Verdict
Adopt dual-strategy context bounding: text-preserving image pruning for vision models with big windows, turn-dropping for small windows; adapt the engine-type list and budget semantics; omit nothing structural. The backwards-walk-with-inner-delete and all-user reflector transcript are the two details porters get wrong.
