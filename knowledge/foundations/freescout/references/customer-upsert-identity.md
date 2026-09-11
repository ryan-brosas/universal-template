<!-- capsule-v2 -->
# Customer upsert & email identity — how do you turn arbitrary inbound addresses into deduplicated customer records?

**Source:** FreeScout AGPL-3.0 `master@ab2772536811d5de6e23121c5d086aeb50f3db2c`; Codebase Memory `ext-freescout`. **Question:** What does "find-or-create customer by email" do exactly — including name parsing, multi-email customers, and the side-effectful CC sanitizer?

## Customer::create
**Path/Symbol:** `app/Customer.php:936-1000` (`create`), `:1141+` (`createWithoutEmail`), name parser `parseName`, sanitizer `app/Email.php:sanitizeEmail`.
**Signature:** `public static function create($email, $data = []): ?Customer` (null when email unsanitizable).
**Data Shape:** emails live in a SEPARATE `emails` table (`Email::where('email')`) pointing at customers — one customer can own many addresses; `$data` accepts first_name/last_name/phones/etc.

### Decisive source
```php
// app/Customer.php:936-982 — upsert keyed on sanitized email
$email = Email::sanitizeEmail($email);
if (!$email) { return null; }
$email_obj = Email::where('email', $email)->first();
if ($email_obj) {
    $customer = $email_obj->customer;
    if (!$customer) { $customer = new self(); }        // orphaned email row heals here
} else {
    $customer = new self();
    $email_obj = new Email();
    $email_obj->email = Email::sanitizeLength($email);
    $new = true;
}
if ($customer->setData($data, false) || !$customer->id) { $customer->save(); }
if (empty($email_obj->id) || !$email_obj->customer_id || $email_obj->customer_id != $customer->id) {
    ... $email_obj->customer()->associate($customer); $email_obj->save();
}
if ($new) { \Eventy::action('customer.created', $customer); }
```
Name update on match is deliberately DISABLED (commented block :952-962) — an existing customer's name never silently changes from new mail.

**Bulk creation during fetch:** `FetchEmails.createCustomers($emails)` (:1821-1840) runs for From+ReplyTo+To+Cc+Bcc of EVERY imported message; each item's `personal` header goes through `Customer::parseName` (first/last split) — so all participants exist as customers before threading. The mailbox's own addresses were once excluded; that filter is commented out (:1824-1827), mailbox participants get customer rows too.

## Conversation::sanitizeEmails — the side-effectful setter
**Path/Symbol:** `app/Conversation.php:1072-1100`.
**PORTER TRAP:** the CC/BCC setters (`setCc` :1022-1031 / `setBcc` :1036-1045) call this sanitizer, and it CREATES CUSTOMERS from `"Name <email>"` strings it parses out of recipient lists — a write-path side effect hiding inside what looks like input validation. Dedupe via `array_unique` + JSON encode with `\Helper::jsonEncodeUtf8`; empty list stores NULL not '[]'.
**Probe:** `grep -c "sanitizeLength" app/Customer.php` (= 2 — the two email-object write sites) and `grep -c "Customer::create(" app/Console/Commands/FetchEmails.php` (= 2 — saveCustomerThread :1187 + createCustomers :1838; `app/Conversation.php` sanitizer adds one more).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-freescout", query: "Customer create email", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt separate-email-table identity with orphan healing, sanitize-before-everything, and never-mutate-name-on-match; adapt the parseName heuristics to your locale conventions; decide EXPLICITLY whether your CC setter should create customers (FreeScout says yes). Direct tests: tests/Feature/ConversationChangeCustomerTest.php covers the conversation-side swap; no direct unit test for create().
