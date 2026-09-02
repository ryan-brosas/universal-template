# Telegram long-poll listener — how do agent turns keep grammY polling alive without a callback deadlock?

**Source:** copilotkit (MIT), `main@e9387e04835545c45744b791aee7c9c03520be31`; Codebase Memory `ext-copilotkit`. **Question:** When an agent turn needs a human confirmation (`confirm_write` → `awaitChoice`), how does the Telegram listener keep grammY's sequential getUpdates poll alive?

## Loop-guard (the load-bearing invariant)
**Path/Symbol:** `packages/channels-telegram/src/listener.ts` (599L) — text+command handlers; `adapter.ts` (742L) — `TelegramAdapter implements PlatformAdapter` (`:69`), webhook + long-poll wiring (`:216` `server.listen`), command registration with slash→underscore naming (`:569`, e.g. `/file-issue` → `/file_issue`).

- `listener.ts` `:240-249`: the turn is fired WITHOUT awaiting:
```ts
// CRITICAL: run the turn WITHOUT blocking grammY's poll loop. grammY's
// built-in long polling processes updates SEQUENTIALLY — it awaits one
// update's handler before fetching the next. If we awaited the full turn
// here, a blocking human-in-the-loop step (confirm_write → awaitChoice)
// would pause polling indefinitely: the callback_query that resolves the
// choice can only arrive via the next getUpdates, which never happens while
// this handler is blocked. …
void Promise.resolve(sink.onTurn({…}))
```
- `callback_query:data` (`:533-555`): ack FIRST in its own try/catch (`:537-542` — stale-button "query is too old" must not strand the `awaitChoice` waiter), then dispatch inside a second try/catch (`:546-554`) so a decode/handler throw never escapes into grammY's loop and crashes the bot.
- `message_reaction` (`:558-571`): LOOP GUARD — a reaction echo of the bot's own `setMessageReaction` egress would come back as a user update and self-loop; guard is `reactor?.id === botUserId` (mirrors the message handlers' `from?.id` guard and Discord's `user?.bot` skip).
- `interface ConversationKey { chatId: string; scope: string }` (`types.ts:11-20`): DM scope is the sentinel `"dm"`, group/forum scope is the thread id — a flat store key string, so conversations from different chats never collide.

## Why it matters (porting contract)
`attachToFunction`→`scrollInfo`-style listener fan-out: N consumers share one measurement/notify pairing — here, ONE grammalls bot instance fans `onTurn`/demo`onInteraction`/… to the platform adapter; the adapter shields the bot from re-entering its own handlers. The core invariant to adopt is **never await a blocking agent step inside the poll handler**, and **never** let a callback-stage throw escape into the transport's own event loop — otherwise the next `getUpdates` never issues and the process drains silently (a deadlock, not a crash).

## Verdict
Adopt the void-turned async pattern and the three isolation layers (per-ack try/catch, per-dispatch try/catch, reaction echo guard). Adapt to your bot framework: the deadlock is framework-general, not grammy-specific — any long-poll transport with a sequential update pipeline needs the same "fire-and-forget agent turn + isolated handler errors" shape. Tests: `adapter.test.ts` (350L) present upstream; if no deps are installed, read the test source and record the unrun-test caveat (upstream suite not executed here).
