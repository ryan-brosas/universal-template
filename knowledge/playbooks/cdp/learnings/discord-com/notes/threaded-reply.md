# Discord web: threaded reply mechanics

This is the knowledge-playbook copy of the registry. The `browser-harness-js` CLI on this machine
loads `learnings/` from its own install tree, so `learnings('discord-com', ...)` may report no
manifest even though the files are here. Import the tool directly instead:
`await import('/home/utopia/.agents/knowledge/playbooks/cdp/learnings/discord-com/tools/reply_to_message.mjs')`
and call `replyToMessage({ session }, args)`. The REPL daemon caches modules by URL, so after an edit
import with a `?v=N` suffix or the old code keeps running.

Selectors and behaviours observed live on 2026-09-25 in large public servers. Hashes in class
names change with releases, so match with substring or case-insensitive tests rather than
exact class strings.

## Message rows

- Each row is a `li` with `id="chat-messages-<channelId>-<messageId>"`.
- The row's own body is `[id="message-content-<messageId>"]`. A reply row also contains a quoted
  preview with its own `message-content-<quotedId>`, so taking the first content descendant of a
  row returns somebody else's message. Always resolve the id you mean.
- Discord virtualises the list: only visible rows are in the DOM, so a message outside the
  rendered window (common when you open a permalink anchor) is simply absent, and a message just
  sent often has to be confirmed at the channel end rather than at the anchor.

## Reply control

- The hover toolbar is not rendered until a real mouse move lands on the row. A DOM-dispatched
  `mouseover` does nothing; `Input.dispatchMouseEvent` with `mouseMoved` does. Two moves a couple
  of pixels apart are enough, and the row has to be visible: `scrollIntoView({block:'center'})`
  first, otherwise the toolbar can stay hidden behind the sticky header and no Reply button exists.
- The toolbar exposes `Add Reaction`, `Reply`, `Forward`, `More` and quick-reaction buttons, all
  with `aria-label` values. `Add Reaction` and `Reply` are plain `div[role=button]`, so match on the
  accessible name rather than the tag.
- A DOM `element.click()` on the Reply button enters reply mode. A CDP right-click on the message
  opened no context menu in the tested client, so the context-menu route is not dependable.
- Reply mode shows a composer bar whose class matches `/replybar/i` (and which is not the
  `repliedMessage*` preview markup), and the bar text starts with `Replying to <author>`. That bar
  names the author, not the message body, so a body match against it always fails: verify the
  author from the source row instead, and check the class plus an empty composer. Read that author
  from the row's own header: a reply row also carries the quoted author's username inside its
  `repliedMessage` block, so a plain `querySelector` on the row returns the wrong person.

## Aborts

- An aborted attempt must not strand text in the composer. `typed-mismatch` now clears what it typed
  and reports `evidence.cleanupCleared`; a draft left behind looks like a half-sent message to anyone
  reading the channel later.
- A composer that was empty at preflight can turn non-empty once reply mode is entered, which is how a
  truncated stray draft produced a `typed-mismatch` on a channel that had no draft beforehand.

## Tabs

- Pass `targetId` to reuse one owned tab for a whole session. Creating a tab per reply is visible
  churn in a browser the user is watching, and it throws away the warm channel page between passes.
  With a reused tab the tool detaches its flat session at the end instead of closing the tab.

## Composing and submitting

- The composer is `[class*=channelTextArea] [role=textbox]`, a contenteditable div. Its text content
  can be a lone BOM (`\uFEFF`) when empty, so trim that before deciding whether it holds a draft.
- `Input.insertText` places the whole string in one shot; do not type character by character, and do
  not clear the composer blindly since channel drafts can be shared between tabs.
- Clearing a composer needs a genuine caret. Selecting the editor contents from the page, calling
  `execCommand('delete')`, or sending Backspace without clicking first are all reverted by the
  editor on its next render. A real mouse click into the composer, then Ctrl+A and Backspace, is
  what actually empties it. Escape cancels reply mode but leaves the text behind.
- One Enter (keyDown + keyUp with `text: '\r'`) submits. Afterwards the composer is empty but the
  submitted message id may differ from the optimistic one, so locate the message by exact text at
  the channel end, then reopen its permalink and check text, author and quoted source.

## Cost of getting this wrong

Every one of these was an observed failure, not a hypothesis: the quoted-preview mix-up, the
missing toolbar after a DOM-only hover, the missing toolbar without `scrollIntoView`, the absent
context menu, a search for the sent row at the anchor instead of the channel end, and a
near-miss verdict treated as a stronger approval than it was.
