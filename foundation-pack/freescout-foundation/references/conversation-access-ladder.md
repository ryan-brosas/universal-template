<!-- capsule-v2 -->
# Conversation access ladder — how does mailbox-scoped RBAC decide who may view, edit, or delete a ticket?

**Source:** FreeScout AGPL-3.0 `master@ab2772536811d5de6e23121c5d086aeb50f3db2c`; Codebase Memory `ext-freescout`. **Question:** What is the exact permission order for conversation actions when a user can be admin, non-member of the mailbox, member with "only assigned" restriction, or holder of granular permission bits?

## ConversationPolicy
**Path/Symbol:** `app/Policies/ConversationPolicy.php:22-130`.
**Signature:** standard Laravel policy methods `view/update/delete(User $user, Conversation $conversation)`, plus static-ish helpers.
**Data Shape:** roles: `User::ROLE_USER=1 / ROLE_ADMIN=2` (User.php:45-46); permissions bitmask constants PERM_DELETE_CONVERSATIONS=1 … PERM_ONLY_ASSIGNED_TICKETS=11 (User.php:89-95); membership = pivot row in `mailbox_user` (`Conversation::userHasAccessToMailbox`, Conversation.php:2755-2760 — plain EXISTS query).

### Decisive source
```php
// app/Policies/ConversationPolicy.php:22-33 + 119-130
public function view(User $user, Conversation $conversation) {
    if ($user->isAdmin()) { return true; }
    if ($conversation->userHasAccessToMailbox($user->id)) {
        return $this->checkIsOnlyAssigned($conversation, $user);   // maybe user sees only assigned
    }
    return false;
}
public function checkIsOnlyAssigned($conversation, $user) {
    if (!\Eventy::filter('conversation.is_user_assignee', $conversation->user_id == $user->id, ...)
        && $conversation->created_by_user_id != $user->id
        && $user->canSeeOnlyAssignedConversations()) {
        return false;
    }
    return true;
}
```
delete() (:82-100) inserts ONE extra gate before the shared ladder: `!$user->hasPermission(User::PERM_DELETE_CONVERSATIONS)` ⇒ false (new conversations without id pass trivially). move() (:110-117) is conversation-independent: true if the user can view >1 mailbox or more than one mailbox exists.

**Permission decode:** `User::hasPermission($permission)` (User.php:975-992): global default from `config('app.user_permissions')` (base64 JSON env override) FIRST, then per-user `$this->permissions[$permission]` overrides it — per-user false beats global true and vice versa. `canSeeOnlyAssignedConversations()` (User.php:1334) reads the same map for PERM_ONLY_ASSIGNED_TICKETS.
**Flow:** every check is admin-bypass → membership gate → only-assigned narrowing → (delete only) bit check. The SAME ladder is reused outside HTTP: the fetcher refuses agent replies by email when `$user->can('view', $prev_thread->conversation)` fails (FetchEmails.php:1029), so email is not a privilege escalation path.
**Invariant:** "only-assigned" narrows but never widens; creator (`created_by_user_id`) is exempt from narrowing even if not currently the assignee; assignee test consults an Eventy filter so modules can redefine "assignee" without touching the policy. Membership is checked on the CONVERSATION'S mailbox at call time — no caching layer may outlive a membership change unless invalidated (viewCached variant uses `users_cached` for read paths only).
**Probe:** `grep -c "isAdmin()" app/Policies/ConversationPolicy.php` (= 4) and `grep -c "userHasAccessToMailbox" app/Policies/ConversationPolicy.php` (= 3).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-freescout", query: "ConversationPolicy view", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt admin→membership→only-assigned(+creator exemption) ordering and global-default/per-user-override permission resolution; adapt Laravel policies+Eventy to your framework's hooks; omit the cached relationship variants unless you have an equivalent invalidation story. Direct tests: tests/Feature/ConversationChangeCustomerTest.php exercises policy adjacent flows; no direct policy unit tests upstream.
