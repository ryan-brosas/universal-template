<!-- capsule-v2 -->
# IMAP fetch loop — how do you page a mailbox without silently dropping the newest emails?

**Source:** FreeScout AGPL-3.0 `master@ab2772536811d5de6e23121c5d086aeb50f3db2c`; Codebase Memory `ext-freescout`. **Question:** How does the fetcher decide when to stop paging so a short page can't lose later (newest) messages, and what happens when SEARCH or charset fails mid-loop?

## FetchEmails::fetch — count-driven pagination
**Path/Symbol:** `app/Console/Commands/FetchEmails.php:216` (`fetch`, 216–381; pagination core 271–377).
**Signature:** `public function fetch($mailbox)` — no return value; throws on INBOX-level errors only.
**Data Shape:** `$page_size = (int)config('app.fetching_bunch_size')`; Webklex `Query` is 1-indexed (`limit($page_size, $page)`, pages start at 1); `$total_messages = $count_query->count()` from a plain IMAP SEARCH.

### Decisive source
```php
// app/Console/Commands/FetchEmails.php:294-312
$count_query = $folder->query()->since(now()->subDays($this->option('days')))->leaveUnread();
if ($unseen) { $count_query->unseen(); }
...
$total_messages = $count_query->count();          // plain SEARCH count up front
$total_pages = ($page_size > 0) ? (int) ceil($total_messages / $page_size) : 1;

for ($page = 1; $page <= $total_pages; $page++) { ... $messages_query->limit($page_size, $page); ...
```
The comment block at :274-293 records WHY: driving the loop off `while (count($messages) == $page_size)` silently dropped the NEWEST emails (#4624) — one message failing to materialize made a bunch come back short and stopped before the later bunches that hold the newest mail under `fetch_order=asc`.

**Flow:** connect (`MailHelper::getMailboxClient` → `$client->connect()`) → enumerate configured IMAP folders (`$mailbox->getInImapFolders()`; missing folder logs and continues) → per folder compute `$total_messages` → loop pages 1..ceil(total/page_size) → per page re-run the same query with `limit(page_size, page)` → sort messages chronologically (`sortMessage`) → `processMessage()` each.
**Invariant:** the page count comes from an independent SEARCH COUNT, never from materialized batch size. Known documented caveat (:290-293): this assumes a stable search set across pages; with `fetch_unseen=1` marking messages `\Seen` mid-loop shrinks the unseen set between pages and shifts `forPage()` — a pre-existing drift (#4047) deliberately NOT fixed here. A porter must not "simplify" back to count-of-page termination.
**Probe:** `grep -c 'ceil($total_messages / $page_size)' app/Console/Commands/FetchEmails.php` (= 1; anchored at repo root).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-freescout", query: "fetch emails mailbox folders", limit: 10, fields: ["signature","name","file"] });
```

## Charset retry ladder
On `'The specified charset is not supported'` in `$client->getLastError()` (:336-352): rebuild the query with `->setCharset(null)`, refetch, and latch `$no_charset = true` so ALL subsequent queries for this run skip charset negotiation (MS-mailbox workaround, issue #176). A failed SEARCH COUNT degrades to `$total_messages = $page_size` (:303-309) — one guaranteed page instead of fetching nothing.

## Connection-throttle backoff
**Path/Symbol:** `app/Console/Commands/FetchEmails.php:99-181`.
Per-mailbox inter-connection sleep starts at 20 ms and grows +20 ms per mailbox up to MAX_SLEEP 500000 µs (:103-127). On `'connection setup failed'` it adds 500 ms, sleeps MAX_SLEEP once, and retries `executeFetch` exactly one more time before recording the error (:136-165). POP3 duplicate-import races surface as SQLSTATE 23000 duplicate-entry errors which are swallowed silently (:160-163) because two concurrent fetchers legitimately race the same old email.

## Verdict
Adopt count-driven pagination + independent SEARCH COUNT + charset-latch + bounded single-retry backoff as the portable contract; adapt Webklex Query specifics (`limit(size, page)`, `leaveUnread`, `unseen`) to your IMAP client; omit the Laravel scheduler wiring around it. Direct tests: none upstream for the loop itself (WebklexTest covers message parsing fixtures only) — behavior claims pinned by source lines above.
