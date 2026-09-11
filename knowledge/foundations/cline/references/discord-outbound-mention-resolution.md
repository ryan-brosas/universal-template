<!-- capsule-v2 -->
# Discord outbound mention resolution — how do you turn agent-written @display-names into real mention ids without ever mis-resolving a fuzzy match?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** The agent writes plain text like `@alice can you check this?` — how do you resolve that to `<@user_id>` for Discord delivery while guaranteeing a wrong user is never pinged?

## Exact-match-only guild search with adapter-split repair
**Path/Symbol:** `apps/cli/src/connectors/adapters/discord.ts:resolveDiscordOutboundMentions` (:497-540) + `pickDiscordMemberByName` (:462-477) + `resolveDiscordMentionName` (:479-495).
**Signature:** `resolveDiscordOutboundMentions(input: { botToken: string; threadId: string; text: string }): Promise<string>`.
**Data Shape:** In: agent reply text + the thread id (decoded `discord:{guild}:{channel}[:thread]`). Out: text with resolved names replaced by `<@id>` mentions; unresolved names pass through verbatim.

### Decisive source
```ts
const exact = members.filter((member) => {
    const user = member.user;
    return [member.nick, user?.username, user?.global_name ?? undefined].some(
        (name) => normalizeDiscordLookupName(name) === normalizedQuery,
    );
});
if (exact.length === 1) return exact[0];
return undefined;   // zero or multiple exact matches resolve to NOTHING
```

**Flow:** decode the guild from the thread id (DMs and `@me` return text unchanged; no `@` in text short-circuits) → scan with a mention regex that matches BOTH `@name` and the adapter-split form `<@base>-suffix` (the chat SDK breaks hyphenated display names across the mention boundary, so `<@cline>-test-bot` must resolve as `cline-test-bot`) → skip pure-numeric 15-25 digit names (already ids) and already-attempted names → guild member search (`limit=10`) per candidate → replace only UNIQUE exact normalized matches → when zero replacements resolved, re-apply the regex to restore the exact original text rather than risk reformatting.
**Invariant:** (1) A fuzzy near-match (`team-alice-bot` for `@alice`) is REFUSED — pinging the wrong user is worse than leaving plain text. (2) Unresolved names survive verbatim; the agent's text is never dropped. (3) The no-replacement path reconstructs the original string exactly.
**Probe:** `apps/cli/src/connectors/adapters/discord.test.ts` — "resolves outbound Discord mention names to user mention ids" (`@cline-test-bot` → `<@1509620637721821224>`), "repairs adapter-split hyphenated Discord mention names before resolving" (`<@cline>-test-bot` resolves), "does not resolve outbound mentions from non-exact Discord member search results" (`@alice` stays `@alice`).

## Get live surrounding code
**Retrieve:** *(canonical call for a connected session — NOT executed this pass)*
```ts
await mcp.codebase_memory.get_code_snippet({ project: "cline", file: "apps/cli/src/connectors/adapters/discord.ts", symbol: "resolveDiscordOutboundMentions" });
```

## Verdict
Adopt exact-match-only name resolution with an explicit split-repair pattern for platform-mangled names, and the never-ping-the-wrong-user refusal rule. Adapt the search endpoint and mention syntax per platform. Omit nothing — the refusal path is the invariant. Coverage caveat: fully test-pinned including the fuzzy-refusal case.
