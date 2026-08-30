<!-- capsule-v2 -->
# Mention autocomplete input path — how does @-completion resolve agent names inside the overlay input?

**Source:** pi-messenger-swarm MIT `main@6fe429a4b74ae276a621bb72910d7926fb6b3104`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm`. **Question:** What is the exact Tab-cycling grammar and candidate source for `@name` completion?

## Tab/shift+Tab cycle over registry peers + live workers + @all
**Path/Symbol:** `overlay/actions.ts:handleMessageInput` (:353-455, tab block :367-388), `overlay/actions.ts:collectMentionCandidates` (:280-309), trigger key `overlay/input.ts` :154-159 (`data === '@' || matchesKey(data,'m')`).
**Signature:** `collectMentionCandidates(prefix: string, state, dirs, cwd): string[]`.
**Data Shape:** completion only while input starts with `@` AND contains no space (unless already cycling); accept writes `` `@<name> ` `` with trailing space.

### Decisive source
```ts
if (!input.startsWith('@') || (input.includes(' ') && !cycling)) return;   // no complete after first word
...
for (const agent of getActiveAgents(state, dirs)) {
  if (agent.name === state.agentName) continue;          // never suggest yourself
  ...
}
for (const worker of getLiveWorkers(cwd).values()) {      // spawned workers even pre-join
  if (!seen.has(worker.name)) { seen.add(worker.name); names.push(worker.name); }
}
names.push('all');                                        // @all = channel post sugar
const lower = prefix.toLowerCase();
return names.filter((n) => n.toLowerCase().startsWith(lower));
```
Enter dispatch: `@all <text>` ⇒ sendChannelPost; `@name <text>` ⇒ DM feed event; bare text ⇒ channel post.

**Flow:** typing `@` (or pressing m) opens message mode seeded with `@`; Tab collects candidates once then cycles modulo length; shift+tab reverses; ANY printable char or backspace resets candidates so stale suggestions can't be accepted. Enter parses the FIRST space as the name/text boundary — a lone `@name` errors with usage hint.
**Invariant:** Candidates are deduped across TWO sources in priority order (registry agents, then live workers incl. not-yet-joined spawns) with self excluded; cycling is allowed to continue AFTER a space only when already mid-cycle (`&& !cycling`) — that guard is what lets you finish choosing after accepting. The `@all` expansion proves mentions are UI-sugar over channel posts, not a separate transport.
**Probe:** direct tests `tests/mention-autocomplete.test.ts::tab completes first matching agent after @` (:79), `::cycles through candidates on repeated tab` (:87), `::includes live workers in candidates` (:114), `::includes @all in candidates` (:120), `::does not complete when input has a space (message already started)` (:126); `grep -c "collectMentionCandidates" overlay/actions.ts` (=2).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm", query: "handleMessageInput collectMentionCandidates mentionCandidates sendDirectMessage", limit: 5 });
```

## Verdict
Adopt two-source deduped candidates + space-gated cycling + `@all` channel-post sugar; adapt keys; preserve the reset-on-any-edit rule or ghost completions get accepted.
