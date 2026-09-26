# Discord web: reading surfaces

This is the knowledge-playbook copy of the registry. `browser-harness-js` loads `learnings/` from
its own install tree, so import the tool by path and bump the `?v=N` query after each edit:

```js
const m = await import('/home/utopia/.agents/knowledge/playbooks/cdp/learnings/discord-com/tools/read_surfaces.mjs?v=1')
await m.listGuildRail({ session })
```

Selectors and behaviours observed live on 2026-09-25/26 in large public servers. Class hashes change
with releases, so these match with substrings (`[class*=hiddenVisually]`) rather than exact class
names. Reply mechanics and the message-row traps are in `threaded-reply.md`.

| Surface | Selector | What it yields |
| --- | --- | --- |
| Guild rail | `[data-list-item-id^="guildsnav___"]` | servers (`aria-level` 1, or 2 inside an open folder) and folders (`div[class*=folderButton]`) |
| Channel list | `[data-list-item-id^="channels___"]` | real channels are `<a href="/channels/<gid>/<cid>">`; `aria-label` gives name and kind |
| Forum posts | `[data-list-item-id="forum-channel-list-<cid>___<tid>"]` | thread id, and `aria-label` `Post <title>, <n> message(s)` |
| Channel tail | `li[id^=chat-messages-]` | rows, each resolved by its own `message-content-<id>` |

## Guild rail

- A server row is `div[class*=wrapper]`; the visible pill has no accessible name of its own, so the
  name sits in a visually hidden span whose text reads `Omacom` or, when unread,
  `Unread messages, Omacom`. Strip that prefix: reading `innerText` alone returns the unread
  clause as part of the name.
- A folder row is `div[class*=folderButton]` with `aria-expanded` and
  `aria-owns="folder-items-<id>"`, and its hidden span concatenates members before the word
  `folder`: `CheapInfra, Makora, wafer, Fireworks.ai, XiaomiMiMo, Neuralwatt, Lilac, ..., folder`,
  plus `, 2,961 unread mentions` on a folder with unread traffic. The trailing `...` means the
  member list is truncated, not that the folder holds a server called `...`.
- Server rows carry `aria-level` 1 at the top of the rail and 2 inside an open folder, so the two
  kinds are distinguishable without parsing text. `aria-setsize` on a level-1 row (38 observed) is
  the number of top-level rows, folders included, while a level-2 row's `aria-setsize` (8 for the
  CheapInfra folder) is that folder's member count.
- Consequence for counting: 73 `guildsnav___` items but 38 top-level rows, so a plain item count
  overstates servers and mixes folders into the server list. Count level-1 rows and read the folder
  flag; an earlier pass reported a flat server list because folder rows and their children were both
  being read as servers.

## Channel list

- `aria-label` is authoritative and reads `providers (text channel)`, `system-messages (text channel)`,
  `server (category)`, `Events` for the events button. Strip the trailing parenthesised kind to get
  the name, and take `gid`/`cid` from the anchor `href` rather than from the list-item id, which is
  prefixed differently for pseudo-items (`_upcoming-events-<gid>`).
- Parsing `innerText` instead was what broke: an item's text is `Text system-messages Invite to Channel`,
  and one server's sidebar separates name from kind with the U+FE31 presentation-form vertical bar, so
  several channel names came out mangled. Read the attribute.
- The list is lazily rendered per guild. A guild not yet opened this session returns an empty list for
  a few seconds, and a list can still be showing the previous guild's channels, so the tool retries
  and compares channel ids against the previous read before accepting a result.
- Text and forum kinds are both available from the same label suffix, so filter on the kind rather than
  guessing from channel names.

## Forum posts

- Each post row is `forum-channel-list-<forumChannelId>___<threadId>` and its `aria-label` carries
  both the title and the reply count: `Post glm-5.3-flex returning gibberish, 1 message`. Singular
  `message` and an absent count both occur.
- Skip ids without a 15+ digit suffix: the header and the tag navigator share the prefix.
- The same titles also appear in `[role=article]` text, without ids.
- Reading one post is an ordinary channel navigation to `/channels/<gid>/<forumChannelId>/<threadId>`.
  Unresolved: three such navigations with a 4.3-4.6 s wait returned an empty message list while the
  same wait worked on ordinary channels, so a forum thread read is not yet demonstrated. Treat an
  empty thread read as unknown, and retry with a longer wait before calling a post quiet.

## Channel tail

- Rows are `li[id^=chat-messages-]`; take the tail rather than the head, because Discord virtualises
  the list and a permalink anchor renders only part of the surrounding conversation.
- Per row: own text from `[id="message-content-<messageId>"]`, author from `[id^=message-username-]`,
  time from `<time datetime>`, quoted preview from `[class*=repliedMessage] [id^=message-content-]`.
  The first `message-content` descendant of a row can belong to somebody else's quoted message.
- An empty read is unknown, not an idle channel. `readChannelEnd` reports `attempts` so the caller can
  tell "polled and still nothing rendered" from "no traffic".
- Polling beats re-navigating. A first version of the tool re-navigated the channel on every attempt
  and returned zero rows after three tries for Maki Community `#general`
  (`1543246530905907263`), while a single 6.5 s wait on the same URL found 48 rows. Navigate once,
  poll for rows, then allow one re-navigation: that channel then read on its second attempt, and read
  again as the second entry of a series. The cause of the difference is not established; the shape
  that works is.

## One browser call at a time

Two overlapping CDP calls into the same Discord session were observed to do real damage: one send
was refused with `composer-dirty` because a concurrent read navigated the same tab, and channel reads
returned the previous guild's channels. `readChannelSeries` exists so a multi-channel read is one
serial loop instead of a `Promise.all`, and it is what the CoralBricks engagement passes use.
