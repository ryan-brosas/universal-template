<!-- capsule-v2 -->
# Slack bot-mention strip boundary — how do you strip a leading self-mention without corrupting look-alike ids or dropping bare pings?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** When a chat platform flattens `<@BOT_ID>` mentions into raw text, how do you remove only the bot's own leading mention without eating a longer id that starts with the same digits?

## Leading-mention strip with id-boundary lookahead
**Path/Symbol:** `apps/cli/src/connectors/adapters/slack.ts:stripSlackBotMention` (:216-245).
**Signature:** `stripSlackBotMention(text: string, botUserId: string | undefined): string`.
**Data Shape:** In: message text + the authenticated bot user id (adapter or event envelope). Out: text with leading self-mentions removed, OR the original text unchanged when the strip would empty it.

### Decisive source
```ts
// Matches `<@U123>`, `<@U123|name>` and the SDK-flattened `@U123` form,
// repeated when a user mentions the bot more than once up front.
//
// The angle-bracket forms are delimited by `>`, but the flattened form has no
// closing delimiter, so it needs an explicit boundary. Without one, `@U123`
// also matches the start of a longer id belonging to someone else, turning
// `@U1234 help` into `4 help`. Slack ids are uppercase alphanumeric, so a
// complete mention is one that is not followed by another id character.
// `\b` cannot express this: ids end in word characters, so `@U123\b` still
// matches inside `@U1234`.
const leadingMention = new RegExp(
	`^(?:\\s*(?:<@${escapedBotId}(?:\\|[^<>]*)?>|@${escapedBotId}(?![A-Za-z0-9]))[\\s,:]*)+`,
);
const stripped = text.replace(leadingMention, "");
return stripped.trim() ? stripped.trimStart() : text;
```

**Flow:** SDK flattens `<@U123>` → `@U123` and deliberately leaves the bot's own mention unresolved (so mention detection keeps working) → strip runs ONLY at the text start, matching repeated mentions in all three forms with trailing whitespace/colon/comma → if the result would be empty (bare `@BOT` ping with no content), the ORIGINAL text is returned so the turn still reaches the agent instead of being dropped as empty input.
**Invariant:** (1) A longer id sharing the bot id as a prefix must survive: `@U1234 help` with bot `U123` is untouched — the flattened form needs the `(?![A-Za-z0-9])` lookahead because `\b` is wrong for word-character-terminated ids. (2) Mentions of OTHER users and inline (non-leading) mentions are preserved — the agent must see who was addressed. (3) A bare self-mention is never stripped to emptiness.
**Probe:** `apps/cli/src/connectors/adapters/slack.test.ts` — "strips the leading bot mention from Slack message text" (`@U`, `<@U>`, `<@U|cline>`, `  @U: `, doubled), "keeps mentions of other Slack users whose id starts with the bot id" (`@U1234 help` survives, `@U0B8E8H3U1FX hi` survives, `<@U1234|other>` survives), "keeps a bare Slack bot mention so the turn is not dropped".

## Get live surrounding code
**Retrieve:** *(canonical call for a connected session — NOT executed this pass)*
```ts
await mcp.codebase_memory.get_code_snippet({ project: "cline", file: "apps/cli/src/connectors/adapters/slack.ts", symbol: "stripSlackBotMention" });
```

## Verdict
Adopt the boundary rule: any "strip my own mention" feature must anchor the id with a not-followed-by-id-character lookahead (or an explicit delimiter) and must never strip to empty input. Adapt the mention syntax and id alphabet to the platform. Omit nothing — the failure modes (prefix-eating, empty-input drop) are the whole point of the capsule. Coverage caveat: fully test-pinned including the adversarial prefix cases.
